"""Lead Workflow v2: the five-status state machine (PRD 2026-08-20).

Replaces the v1 claim/deadline machinery (`services/claims.py`) and the review
lock/permission gate. The design bet: control comes from an immutable timeline,
not from locks. Operators may take, drop, finish and reopen anything without
asking an admin -- the one thing the system insists on is a comment when they
walk away from unfinished work, because the next operator has to know where it
stopped.

Two invariants the rest of the code leans on:

  * `assigned_to_id` is set if and only if `status == in_progress`.
  * every state change writes exactly one `lead_events` row, in the same
    transaction, and nothing ever updates or deletes one.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import Select, bindparam, case, func, literal, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.lead import (
    EVENT_ADMIN_ASSIGN,
    EVENT_ADMIN_RELEASE,
    EVENT_AUTO_RELEASE,
    EVENT_COMMENT,
    EVENT_FINISH,
    EVENT_HANDOVER,
    EVENT_REOPEN,
    EVENT_STATUS_CHANGE,
    STATUS_APPROVED,
    STATUS_IN_PROGRESS,
    STATUS_NEW,
    STATUS_REJECTED,
    STATUS_WAITING,
    LeadEvent,
    LeadState,
)
from app.models.review import REVIEW_FIELDS, CompanyReview
from app.models.user import User

# An in-progress lead nobody has touched for this long stops counting as held.
# Computed in the WHERE clause of every read and claim rather than swept by a
# background job -- same trick v1 used for `is_overdue`, minus the blocking.
AUTO_RELEASE_HOURS = 4

# Admin attention thresholds (PRD FR-16).
STALE_WAITING_DAYS = 2
HANDOFF_ALERT_COUNT = 3

# The whole state machine. Anything not in here is refused (FR-2).
ALLOWED_TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        (STATUS_NEW, STATUS_IN_PROGRESS),
        (STATUS_WAITING, STATUS_IN_PROGRESS),
        (STATUS_APPROVED, STATUS_IN_PROGRESS),
        (STATUS_REJECTED, STATUS_IN_PROGRESS),
        (STATUS_IN_PROGRESS, STATUS_WAITING),
        (STATUS_IN_PROGRESS, STATUS_APPROVED),
        (STATUS_IN_PROGRESS, STATUS_REJECTED),
    }
)

# Statuses a plain "start work" may take over. Reopening a finished lead is a
# separate, note-bearing action -- it must not happen by accident.
CLAIMABLE_FROM = (STATUS_NEW, STATUS_WAITING)
FINISHED = (STATUS_APPROVED, STATUS_REJECTED)


class LeadError(Exception):
    """Carries the shape the API returns verbatim: {code, message, ...context}.

    `message` is operator-facing Uzbek -- the frontend shows it as-is rather than
    maintaining a parallel table of translations per error code.
    """

    status_code = 409

    def __init__(self, code: str, message: str, **context: object) -> None:
        self.code = code
        self.message = message
        self.context = context
        super().__init__(message)

    def as_detail(self) -> dict:
        return {"code": self.code, "message": self.message, **self.context}


class LeadNotFound(LeadError):
    status_code = 404

    def __init__(self) -> None:
        super().__init__("not_found", "Bunday lead topilmadi.")


# --------------------------------------------------------------------------- #
# Staleness helpers
# --------------------------------------------------------------------------- #


def _stale_cutoff(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) - timedelta(hours=AUTO_RELEASE_HOURS)


def is_stale(state: LeadState | None, *, now: datetime | None = None) -> bool:
    """True when an in-progress lead has gone quiet long enough to be up for grabs."""
    if state is None or state.status != STATUS_IN_PROGRESS:
        return False
    if state.last_activity_at is None:
        return True
    return state.last_activity_at < _stale_cutoff(now)


def effective_status(state: LeadState | None, *, now: datetime | None = None) -> str:
    """What the lead *is* right now, as opposed to what the row literally says.

    A missing row is New; a stale in-progress row is Waiting. Both are computed,
    so a read never has to write.
    """
    if state is None:
        return STATUS_NEW
    if is_stale(state, now=now):
        return STATUS_WAITING
    return state.status


def effective_assignee(state: LeadState | None, *, now: datetime | None = None) -> int | None:
    if state is None or effective_status(state, now=now) != STATUS_IN_PROGRESS:
        return None
    return state.assigned_to_id


def status_sql_expr():
    """The SQL twin of `effective_status`, for list queries.

    Kept next to the Python version on purpose: if one changes and the other
    doesn't, the queue and the detail page start disagreeing about the same lead.
    """
    stale = LeadState.last_activity_at.is_(None) | (
        LeadState.last_activity_at < func.now() - text(f"interval '{AUTO_RELEASE_HOURS} hours'")
    )
    return case(
        (LeadState.status.is_(None), literal(STATUS_NEW)),
        ((LeadState.status == STATUS_IN_PROGRESS) & stale, literal(STATUS_WAITING)),
        else_=LeadState.status,
    )


def assignee_sql_expr():
    """Assignee as the queue should see it -- NULL once the hold has gone stale."""
    return case((status_sql_expr() == STATUS_IN_PROGRESS, LeadState.assigned_to_id), else_=None)


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #


async def get_state(session: AsyncSession, company_id: int, *, fresh: bool = False) -> LeadState | None:
    """`fresh=True` re-reads over the identity map.

    Required after `_conditional_claim`, which writes through raw SQL: without it
    the session hands back the instance it loaded *before* the claim, still
    carrying the old status and assignee.
    """
    stmt = select(LeadState).where(LeadState.company_id == company_id)
    if fresh:
        stmt = stmt.execution_options(populate_existing=True)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_active_lead(session: AsyncSession, operator_id: int) -> LeadState | None:
    """The operator's one in-progress lead, if they still hold it.

    Stale holds are excluded deliberately: a lead the operator forgot about four
    hours ago must not stand between them and their next piece of work. That was
    exactly v1's failure mode, one abstraction up.
    """
    return (
        await session.execute(
            select(LeadState).where(
                LeadState.assigned_to_id == operator_id,
                LeadState.status == STATUS_IN_PROGRESS,
                LeadState.last_activity_at >= _stale_cutoff(),
            )
        )
    ).scalar_one_or_none()


async def visible_to(session: AsyncSession, company_id: int, user: User) -> LeadState | None:
    """Raises LeadNotFound when this user must not even learn the lead exists.

    404 rather than 403 on someone else's in-progress lead (FR-4): a "you may not
    see this" response still tells the operator that a company they can't see is
    being worked on, which is one more thing to wonder about than they need.
    """
    company = await session.get(Company, company_id)
    if company is None:
        raise LeadNotFound()
    state = await get_state(session, company_id)
    if user.role == "admin":
        return state
    if effective_status(state) == STATUS_IN_PROGRESS and state.assigned_to_id != user.id:
        raise LeadNotFound()
    return state


# --------------------------------------------------------------------------- #
# Timeline
# --------------------------------------------------------------------------- #


async def record(
    session: AsyncSession,
    *,
    company_id: int,
    actor_id: int | None,
    type: str,
    from_status: str | None = None,
    to_status: str | None = None,
    note: str | None = None,
) -> LeadEvent:
    """Append one timeline row. `actor_id=None` means the system did it."""
    event = LeadEvent(
        company_id=company_id,
        actor_id=actor_id,
        type=type,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )
    session.add(event)
    await session.flush()
    return event


def require_note(note: str | None, message: str) -> str:
    cleaned = (note or "").strip()
    if not cleaned:
        raise LeadError("note_required", message)
    return cleaned


def require_operator(user: User) -> None:
    """Admins supervise; they do not work leads.

    Enforced here rather than only in the UI, because "admin can also grab a
    lead" quietly breaks two things: the queue counts stop describing operator
    workload, and per-operator throughput starts including a supervisor who was
    only spot-checking. An admin who genuinely needs a lead worked assigns it to
    an operator (`admin_assign`).
    """
    if user.role == "admin":
        raise LeadError(
            "admin_readonly",
            "Admin lead ustida ishlamaydi — kuzatadi. Ishni operatorga biriktiring.",
        )


def check_transition(from_status: str, to_status: str) -> None:
    if (from_status, to_status) not in ALLOWED_TRANSITIONS:
        raise LeadError(
            "invalid_transition",
            "Bu holatdan bunday o'tish mumkin emas. Sahifani yangilab qayta urinib ko'ring.",
            from_status=from_status,
            to_status=to_status,
        )


# --------------------------------------------------------------------------- #
# Claiming
# --------------------------------------------------------------------------- #


_CLAIM_SQL = text("""
    INSERT INTO lead_states (company_id, status, assigned_to_id, assigned_at,
                             last_activity_at, last_actor_id, created_at, updated_at)
    VALUES (:company_id, 'in_progress', :operator_id, now(), now(), :operator_id, now(), now())
    ON CONFLICT (company_id) DO UPDATE
       SET status = 'in_progress',
           assigned_to_id = :operator_id,
           assigned_at = now(),
           last_activity_at = now(),
           last_actor_id = :operator_id,
           updated_at = now()
     WHERE lead_states.status IN :from_statuses
        OR (lead_states.status = 'in_progress'
            AND (lead_states.assigned_to_id = :operator_id
                 OR lead_states.last_activity_at IS NULL
                 OR lead_states.last_activity_at < :stale_at))
    RETURNING id
""").bindparams(bindparam("from_statuses", expanding=True))


async def _conditional_claim(
    session: AsyncSession, company_id: int, operator_id: int, from_statuses: tuple[str, ...]
) -> bool:
    """Take the lead if and only if it is still takeable, in one statement.

    A read-then-write would let two operators both pass the check and both claim;
    the whole point is that the database decides, not the application. The
    ON CONFLICT ... WHERE clause is also where the 4-hour auto-release lives --
    a hold that has gone quiet simply stops satisfying the "is it still theirs?"
    test, with no sweeper job to run (AR-9).

    Returns False when the claim lost the race.
    """
    result = await session.execute(
        _CLAIM_SQL,
        {
            "company_id": company_id,
            "operator_id": operator_id,
            "from_statuses": list(from_statuses),
            "stale_at": _stale_cutoff(),
        },
    )
    return result.first() is not None


async def claim(session: AsyncSession, company_id: int, user: User) -> LeadState:
    """Start (or resume) work on a lead.

    Raises `handover_required` when the operator is already holding something
    else -- the caller turns that into the one dialog that asks for the comment
    and then calls `switch`.
    """
    require_operator(user)
    company = await session.get(Company, company_id)
    if company is None:
        raise LeadNotFound()

    current = await get_state(session, company_id)
    if current is not None and effective_status(current) == STATUS_IN_PROGRESS and current.assigned_to_id == user.id:
        # Already theirs -- reopening the page, not a new claim. Still counts as
        # activity: a long call on a single lead should not let the hold lapse.
        current.last_activity_at = datetime.now(UTC)
        await session.flush()
        return current

    active = await get_active_lead(session, user.id)
    if active is not None and active.company_id != company_id:
        other = await session.get(Company, active.company_id)
        raise LeadError(
            "handover_required",
            f"Sizda tugallanmagan ish bor: {other.name if other else ''}. Uni qoldirish uchun izoh yozing.",
            active_company_id=active.company_id,
            active_company_name=other.name if other else "",
        )

    # Read before the write: the timeline needs the status we came from, and the
    # conditional upsert below cannot report it without a second round trip.
    took_over_stale = is_stale(current)
    prior = effective_status(current)

    if not await _conditional_claim(session, company_id, user.id, CLAIMABLE_FROM):
        raise LeadError(
            "held_by_other",
            "Bu leadni boshqa operator band qilib ulgurdi.",
            company_id=company_id,
        )

    # Taking over a stale hold gets its own line, so the previous operator can see
    # what happened to their lead instead of just finding it gone.
    if took_over_stale:
        await record(
            session,
            company_id=company_id,
            actor_id=None,
            type=EVENT_AUTO_RELEASE,
            from_status=STATUS_IN_PROGRESS,
            to_status=STATUS_WAITING,
            note=f"Avtomatik bo'shatildi — {AUTO_RELEASE_HOURS} soat harakatsizlik.",
        )

    await record(
        session,
        company_id=company_id,
        actor_id=user.id,
        type=EVENT_STATUS_CHANGE,
        from_status=prior,
        to_status=STATUS_IN_PROGRESS,
    )
    return await get_state(session, company_id, fresh=True)


async def _release(
    session: AsyncSession,
    state: LeadState,
    *,
    to_status: str,
    actor_id: int | None,
    event_type: str,
    note: str | None,
) -> LeadState:
    """Move a lead out of in-progress and clear the hold."""
    check_transition(state.status, to_status)
    from_status = state.status
    state.status = to_status
    state.assigned_to_id = None
    state.assigned_at = None
    if actor_id is not None:
        state.last_actor_id = actor_id
    state.last_activity_at = datetime.now(UTC)
    await session.flush()
    await record(
        session,
        company_id=state.company_id,
        actor_id=actor_id,
        type=event_type,
        from_status=from_status,
        to_status=to_status,
        note=note,
    )
    return state


async def _owned(session: AsyncSession, company_id: int, user: User) -> LeadState:
    require_operator(user)
    state = await get_state(session, company_id)
    if state is None or effective_status(state) != STATUS_IN_PROGRESS:
        raise LeadError("not_in_progress", "Bu lead hozir sizda emas. Sahifani yangilang.")
    if state.assigned_to_id != user.id:
        raise LeadError("held_by_other", "Bu lead boshqa operatorda.")
    return state


async def pause(session: AsyncSession, company_id: int, user: User, *, note: str | None) -> LeadState:
    """Put the lead down, with the comment the next operator will read first."""
    state = await _owned(session, company_id, user)
    cleaned = require_note(note, "Ishni qoldirish uchun izoh yozing — keyingi operator qayerda to'xtaganingizni bilishi kerak.")
    return await _release(
        session, state, to_status=STATUS_WAITING, actor_id=user.id, event_type=EVENT_HANDOVER, note=cleaned
    )


async def switch(session: AsyncSession, *, from_company_id: int, to_company_id: int, user: User, note: str | None) -> LeadState:
    """Hand off one lead and pick up another, atomically (NFR-3).

    If the new lead can't be claimed, the old one is untouched -- the operator
    must never end up having dropped their work and gained nothing.
    """
    if from_company_id == to_company_id:
        raise LeadError("invalid_transition", "Bu allaqachon sizning joriy ishingiz.")
    await pause(session, from_company_id, user, note=note)
    return await claim(session, to_company_id, user)


async def finish(session: AsyncSession, company_id: int, user: User, *, result: str, note: str | None) -> LeadState:
    """Approve or reject. No admin in the loop (FR-9)."""
    if result not in FINISHED:
        raise LeadError("invalid_transition", "Noma'lum yakun turi.")
    state = await _owned(session, company_id, user)

    cleaned = (note or "").strip() or None
    if result == STATUS_APPROVED:
        missing = await _unset_fields(session, company_id)
        if missing:
            raise LeadError(
                "fields_incomplete",
                "Tasdiqlash uchun Website va LMS belgilanishi kerak.",
                missing=missing,
            )
    else:
        cleaned = require_note(note, "Rad etish sababini yozing.")

    return await _release(
        session, state, to_status=result, actor_id=user.id, event_type=EVENT_FINISH, note=cleaned
    )


async def reopen(session: AsyncSession, company_id: int, user: User, *, note: str | None) -> LeadState:
    """Correct a finished lead without asking anyone (FR-10).

    The note is mandatory: removing the permission gate only works if the reason
    still ends up on the record.
    """
    require_operator(user)
    state = await get_state(session, company_id)
    if state is None or state.status not in FINISHED:
        raise LeadError("invalid_transition", "Bu lead yakunlanmagan — qayta ochishga hojat yo'q.")
    cleaned = require_note(note, "Qayta ochish sababini yozing.")
    from_status = state.status

    active = await get_active_lead(session, user.id)
    if active is not None and active.company_id != company_id:
        other = await session.get(Company, active.company_id)
        raise LeadError(
            "handover_required",
            f"Sizda tugallanmagan ish bor: {other.name if other else ''}. Uni qoldirish uchun izoh yozing.",
            active_company_id=active.company_id,
            active_company_name=other.name if other else "",
        )

    if not await _conditional_claim(session, company_id, user.id, FINISHED):
        raise LeadError("held_by_other", "Bu leadni boshqa operator band qilib ulgurdi.")

    await record(
        session,
        company_id=company_id,
        actor_id=user.id,
        type=EVENT_REOPEN,
        from_status=from_status,
        to_status=STATUS_IN_PROGRESS,
        note=cleaned,
    )
    return await get_state(session, company_id, fresh=True)


async def comment(session: AsyncSession, company_id: int, user: User, *, note: str | None) -> LeadEvent:
    """A note that changes nothing but the record (FR-13)."""
    state = await _owned(session, company_id, user)
    cleaned = require_note(note, "Izoh bo'sh bo'lishi mumkin emas.")
    state.last_activity_at = datetime.now(UTC)
    state.last_actor_id = user.id
    await session.flush()
    return await record(session, company_id=company_id, actor_id=user.id, type=EVENT_COMMENT, note=cleaned)


async def touch(session: AsyncSession, company_id: int, user: User) -> LeadState:
    """Bump the inactivity clock on a draft save.

    Deliberately writes no timeline row: a keystroke-level audit would bury the
    handover comments the timeline exists to surface (PRD assumption, section 12).
    """
    state = await _owned(session, company_id, user)
    state.last_activity_at = datetime.now(UTC)
    state.last_actor_id = user.id
    await session.flush()
    return state


# --------------------------------------------------------------------------- #
# Admin intervention
# --------------------------------------------------------------------------- #


async def admin_release(session: AsyncSession, company_id: int, admin: User, *, note: str | None) -> LeadState:
    state = await get_state(session, company_id)
    if state is None or state.status != STATUS_IN_PROGRESS:
        raise LeadError("not_in_progress", "Bu lead hozir hech kimda emas.")
    cleaned = require_note(note, "Bo'shatish sababini yozing.")
    return await _release(
        session, state, to_status=STATUS_WAITING, actor_id=admin.id, event_type=EVENT_ADMIN_RELEASE, note=cleaned
    )


async def admin_assign(session: AsyncSession, company_id: int, admin: User, *, operator_id: int, note: str | None) -> LeadState:
    company = await session.get(Company, company_id)
    if company is None:
        raise LeadNotFound()
    operator = await session.get(User, operator_id)
    if operator is None or not operator.is_active:
        raise LeadError("unknown_operator", "Bunday operator topilmadi yoki u faol emas.")
    cleaned = require_note(note, "Biriktirish sababini yozing.")

    state = await get_state(session, company_id)
    from_status = effective_status(state)
    now = datetime.now(UTC)
    if state is None:
        state = LeadState(company_id=company_id)
        session.add(state)
    state.status = STATUS_IN_PROGRESS
    state.assigned_to_id = operator_id
    state.assigned_at = now
    state.last_activity_at = now
    state.last_actor_id = admin.id
    await session.flush()
    await record(
        session,
        company_id=company_id,
        actor_id=admin.id,
        type=EVENT_ADMIN_ASSIGN,
        from_status=from_status,
        to_status=STATUS_IN_PROGRESS,
        note=cleaned,
    )
    return state


# --------------------------------------------------------------------------- #
# Review fields
# --------------------------------------------------------------------------- #


async def _unset_fields(session: AsyncSession, company_id: int) -> list[str]:
    rows = (
        (await session.execute(select(CompanyReview).where(CompanyReview.company_id == company_id))).scalars().all()
    )
    by_field = {r.field: r for r in rows}
    return [f for f in REVIEW_FIELDS if by_field.get(f) is None or by_field[f].available is None]


async def save_draft(session: AsyncSession, company_id: int, user: User, *, fields: dict[str, dict]) -> None:
    """Upsert whatever the operator has decided so far. Partial is fine (FR-19)."""
    existing = (
        (await session.execute(select(CompanyReview).where(CompanyReview.company_id == company_id))).scalars().all()
    )
    by_field = {r.field: r for r in existing}
    now = datetime.now(UTC)
    for field, data in fields.items():
        if field not in REVIEW_FIELDS or data is None:
            continue
        row = by_field.get(field)
        if row is None:
            row = CompanyReview(company_id=company_id, field=field)
            session.add(row)
        row.available = data.get("available")
        row.comment = data.get("comment")
        row.filled_by_id = user.id
        row.filled_at = now
    await session.flush()


# --------------------------------------------------------------------------- #
# What can this user do right now?
# --------------------------------------------------------------------------- #


def available_actions(state: LeadState | None, user: User, *, unset_fields: list[str] | None = None) -> list[str]:
    """The single source of truth for which buttons exist.

    The frontend renders this list rather than re-deriving the rules, so there is
    only one place where "can I approve this yet?" is answered.
    """
    status = effective_status(state)
    actions: list[str] = []

    # Admins observe and redirect work; they never hold a lead themselves.
    if user.role == "admin":
        if status == STATUS_IN_PROGRESS:
            actions.append("admin_release")
        else:
            actions.append("admin_assign")
        return actions

    is_mine = status == STATUS_IN_PROGRESS and state is not None and state.assigned_to_id == user.id
    if status in (STATUS_NEW, STATUS_WAITING):
        actions.append("start")
    elif is_mine:
        actions += ["pause", "comment", "reject"]
        if not unset_fields:
            actions.append("approve")
    elif status in FINISHED:
        actions.append("reopen")
    return actions


# --------------------------------------------------------------------------- #
# Queue query building blocks
# --------------------------------------------------------------------------- #


def base_query(user: User) -> Select:
    """Companies joined to their (possibly absent) lead state, minus what this
    user must not see.

    An OUTER join with COALESCE instead of backfilling a row per company: the
    scrape pipeline owns `companies` and must stay free to insert without the
    review domain noticing (AD-2).
    """
    stmt = select(Company, LeadState).outerjoin(LeadState, LeadState.company_id == Company.id)
    if user.role != "admin":
        stmt = stmt.where(
            or_(
                status_sql_expr() != STATUS_IN_PROGRESS,
                LeadState.assigned_to_id == user.id,
            )
        )
    return stmt


def apply_status_filter(stmt: Select, status: str | None, user: User) -> Select:
    if status is None or status == "all":
        return stmt
    if status == "mine":
        return stmt.where(status_sql_expr() == STATUS_IN_PROGRESS, LeadState.assigned_to_id == user.id)
    if status == STATUS_IN_PROGRESS:
        # Only an admin ever asks for this tab; operators get theirs via "mine".
        return stmt.where(status_sql_expr() == STATUS_IN_PROGRESS)
    return stmt.where(status_sql_expr() == status)
