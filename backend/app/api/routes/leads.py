"""Lead Workflow v2 API.

Replaces `/api/reviews`, `/api/claims`, `/api/claim-requests` and
`/api/permission-requests`. Every state-changing route delegates to
`services.leads` -- the routes translate HTTP, they do not hold rules.
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import any_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_admin
from app.models.company import Company
from app.models.lead import (
    EVENT_HANDOVER,
    LEAD_STATUSES,
    STATUS_APPROVED,
    STATUS_IN_PROGRESS,
    STATUS_REJECTED,
    STATUS_WAITING,
    LeadEvent,
    LeadState,
)
from app.models.review import FIELD_LMS, FIELD_WEBSITE, REVIEW_FIELDS, CompanyReview
from app.models.user import User
from app.schemas.lead import (
    AssignIn,
    CategoryOut,
    DraftIn,
    FinishIn,
    LeadAttentionItemOut,
    LeadDetailOut,
    LeadEventOut,
    LeadFieldOut,
    LeadListItemOut,
    LeadListOut,
    NoteIn,
    SwitchIn,
)
from app.services import leads as leads_service
from app.services.notifications import notify
from app.services.ws_manager import manager

router = APIRouter(prefix="/leads", tags=["leads"])

# Tabs the queue offers. "mine" is a view over in_progress (the caller's own),
# not a stored status; "all" is the admin's unfiltered view.
QUEUE_TABS = ("new", "mine", STATUS_IN_PROGRESS, STATUS_WAITING, STATUS_APPROVED, STATUS_REJECTED, "all")


async def _broadcast(company_id: int, status: str) -> None:
    """Nudge every open queue so it drops a lead somebody else just took (FR-15).

    Fire-and-forget by design: the REST list is still authoritative, so a client
    that missed the frame simply refreshes a moment later.
    """
    await manager.broadcast({"kind": "lead", "company_id": company_id, "status": status})


# --------------------------------------------------------------------------- #
# Listing
# --------------------------------------------------------------------------- #


def _apply_filters(stmt, q: str | None, category: str | None):
    if q:
        stmt = stmt.where(Company.name.ilike(f"%{q}%"))
    if category:
        # AD-12: exact match within the semicolon-separated tag list, not a
        # substring ILIKE that would confuse sibling categories.
        stmt = stmt.where(category == any_(func.string_to_array(Company.category, "; ")))
    return stmt


@router.get("", response_model=LeadListOut)
async def list_leads(
    status: str = Query(default="new", pattern="^(new|mine|in_progress|waiting|approved|rejected|all)$"),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    actor: str | None = Query(
        default=None,
        pattern=r"^(me|\d+)$",
        description="restrict to leads last acted on by this user: 'me', or an operator id (admin only)",
    ),
    limit: int = Query(default=20, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadListOut:
    status_expr = leads_service.status_sql_expr()

    visible = _apply_filters(leads_service.base_query(user), q, category)
    if actor == "me":
        visible = visible.where(LeadState.last_actor_id == user.id)
    elif actor:
        # "everything Botir touched" -- the question the admin table could not
        # ask. `me` was the only accepted value, which for an admin returns
        # nothing at all, since admins never act on leads by design.
        actor_id = int(actor)
        if user.role != "admin" and actor_id != user.id:
            actor_id = user.id  # an operator may only ever filter to themselves
        visible = visible.where(LeadState.last_actor_id == actor_id)
    filtered = leads_service.apply_status_filter(visible, status, user)

    total = (
        await session.execute(select(func.count()).select_from(filtered.subquery()))
    ).scalar_one()

    rows = (
        await session.execute(
            filtered.add_columns(status_expr.label("effective_status"))
            .order_by(LeadState.last_activity_at.desc().nulls_last(), Company.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()

    # One grouped query for every tab badge (FR-14); the v1 queue paid for a
    # whole second request just to render these numbers. Counted over a subquery
    # rather than `with_only_columns`, which can rebuild the FROM clause from the
    # new column list and silently drop the outer join to lead_states.
    counted = visible.add_columns(status_expr.label("s")).subquery()
    count_rows = (
        await session.execute(select(counted.c.s, func.count()).select_from(counted).group_by(counted.c.s))
    ).all()
    counts = {s: 0 for s in LEAD_STATUSES}
    for s, n in count_rows:
        counts[s] = n
    counts["all"] = sum(counts.values())
    mine = leads_service.apply_status_filter(visible, "mine", user)
    counts["mine"] = (await session.execute(select(func.count()).select_from(mine.subquery()))).scalar_one()

    if not rows:
        return LeadListOut(items=[], total=total, counts=counts)

    company_ids = [r[0].id for r in rows]
    reviews_by_company = await _reviews_for(session, company_ids)
    notes_by_company = await _latest_notes_for(session, company_ids)
    user_names = await _user_names_for(
        session,
        {r[1].assigned_to_id for r in rows if r[1] is not None}
        | {n["actor_id"] for n in notes_by_company.values()},
    )

    items = []
    for company, state, eff_status in rows:
        note = notes_by_company.get(company.id)
        assignee_id = state.assigned_to_id if (state and eff_status == STATUS_IN_PROGRESS) else None
        fields = reviews_by_company.get(company.id, {})
        items.append(
            LeadListItemOut(
                id=company.id,
                name=company.name,
                category=company.category,
                address=company.address,
                phone=company.phone,
                source=company.source,
                status=eff_status,
                assignee_id=assignee_id,
                assignee_name=user_names.get(assignee_id),
                website_available=getattr(fields.get(FIELD_WEBSITE), "available", None),
                lms_available=getattr(fields.get(FIELD_LMS), "available", None),
                last_note=note["note"] if note else None,
                last_note_by=user_names.get(note["actor_id"]) if note else None,
                last_note_at=note["created_at"] if note else None,
            )
        )
    return LeadListOut(items=items, total=total, counts=counts)


async def _reviews_for(session: AsyncSession, company_ids: list[int]) -> dict[int, dict[str, CompanyReview]]:
    """Batched -- the v1 detail loader issued one query per field per row (NFR-2)."""
    rows = (
        (await session.execute(select(CompanyReview).where(CompanyReview.company_id.in_(company_ids))))
        .scalars()
        .all()
    )
    out: dict[int, dict[str, CompanyReview]] = {}
    for r in rows:
        out.setdefault(r.company_id, {})[r.field] = r
    return out


async def _latest_notes_for(session: AsyncSession, company_ids: list[int]) -> dict[int, dict]:
    """Newest commented event per company, in one DISTINCT ON query."""
    stmt = (
        select(LeadEvent.company_id, LeadEvent.note, LeadEvent.actor_id, LeadEvent.created_at)
        .where(
            LeadEvent.company_id.in_(company_ids),
            LeadEvent.note.isnot(None),
            LeadEvent.note != "",
        )
        .order_by(LeadEvent.company_id, LeadEvent.created_at.desc())
        .distinct(LeadEvent.company_id)
    )
    return {
        row.company_id: {"note": row.note, "actor_id": row.actor_id, "created_at": row.created_at}
        for row in (await session.execute(stmt)).all()
    }


async def _user_names_for(session: AsyncSession, ids: set[int | None]) -> dict[int, str]:
    real = {i for i in ids if i}
    if not real:
        return {}
    rows = (await session.execute(select(User.id, User.full_name).where(User.id.in_(real)))).all()
    return {i: name for i, name in rows}


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CategoryOut]:
    """Every category, with its company count, biggest first.

    Previously this pulled all 12k `category` strings into Python and split them
    there, returning bare names in alphabetical order. Two problems: the work
    grows with the table, and -- worse -- an alphabetical list of 3.6k tags is
    not something a person can browse. It opens on "3D печать" and the
    categories that actually hold the database ("Завод в Узбекистане", 1008
    companies) are thousands of rows down, reachable only by typing a name you
    would have to already know.

    So the split, the count and the ordering all happen in SQL, and the count
    travels to the client (AD-17).
    """
    tag = func.btrim(func.unnest(func.string_to_array(Company.category, "; "))).label("tag")
    inner = select(tag).where(Company.category.isnot(None)).subquery()
    rows = (
        await session.execute(
            select(inner.c.tag, func.count().label("n"))
            .where(inner.c.tag != "")
            .group_by(inner.c.tag)
            .order_by(desc("n"), inner.c.tag)
        )
    ).all()
    return [CategoryOut(name=name, count=n) for name, n in rows]


@router.get("/attention", response_model=list[LeadAttentionItemOut])
async def list_attention(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[LeadAttentionItemOut]:
    """Leads that have gone quiet or been passed around (FR-16).

    Both signals are about flow, not blame: nobody is blocked, so the only way an
    admin learns something is stuck is by being shown it.
    """
    cutoff = datetime.now(UTC) - timedelta(days=leads_service.STALE_WAITING_DAYS)

    # `status_sql_expr()`, not the literal column. The rest of the app treats an
    # in_progress lead idle past AUTO_RELEASE_HOURS as waiting; this query used
    # the raw column, so a lead an operator claimed and then vanished on stayed
    # literally `in_progress` forever and never appeared here -- the single most
    # abandoned kind of lead was invisible on the one screen built to surface it.
    stale_rows = (
        await session.execute(
            select(Company, LeadState)
            .join(LeadState, LeadState.company_id == Company.id)
            .where(
                leads_service.status_sql_expr() == STATUS_WAITING,
                LeadState.last_activity_at < cutoff,
            )
            .order_by(LeadState.last_activity_at)
            .limit(50)
        )
    ).all()

    handoff_counts = (
        await session.execute(
            select(LeadEvent.company_id, func.count().label("n"))
            .where(LeadEvent.type == EVENT_HANDOVER)
            .group_by(LeadEvent.company_id)
            .having(func.count() >= leads_service.HANDOFF_ALERT_COUNT)
            .order_by(func.count().desc())
            .limit(50)
        )
    ).all()

    ids = [c.id for c, _ in stale_rows] + [cid for cid, _ in handoff_counts]
    notes = await _latest_notes_for(session, ids) if ids else {}
    holder_names = await _user_names_for(
        session, {st.assigned_to_id for _, st in stale_rows} | {st.last_actor_id for _, st in stale_rows}
    )

    out: list[LeadAttentionItemOut] = []
    seen: set[int] = set()
    now = datetime.now(UTC)
    for company, state in stale_rows:
        seen.add(company.id)
        days = (now - state.last_activity_at).days if state.last_activity_at else None
        out.append(
            LeadAttentionItemOut(
                id=company.id,
                name=company.name,
                status=leads_service.effective_status(state),
                reason="stale",
                waiting_days=days,
                handoff_count=None,
                last_note=(notes.get(company.id) or {}).get("note"),
                # assigned_to_id first: a lead still literally in_progress is one
                # somebody is holding, which is the case worth naming.
                last_holder=holder_names.get(state.assigned_to_id) or holder_names.get(state.last_actor_id),
            )
        )

    if handoff_counts:
        companies = {
            c.id: c
            for c in (
                await session.execute(select(Company).where(Company.id.in_([cid for cid, _ in handoff_counts])))
            )
            .scalars()
            .all()
        }
        states = {
            s.company_id: s
            for s in (
                await session.execute(
                    select(LeadState).where(LeadState.company_id.in_([cid for cid, _ in handoff_counts]))
                )
            )
            .scalars()
            .all()
        }
        for company_id, n in handoff_counts:
            company = companies.get(company_id)
            if company is None or company_id in seen:
                continue
            out.append(
                LeadAttentionItemOut(
                    id=company_id,
                    name=company.name,
                    status=leads_service.effective_status(states.get(company_id)),
                    reason="handoffs",
                    waiting_days=None,
                    handoff_count=n,
                    last_note=(notes.get(company_id) or {}).get("note"),
                )
            )
    return out


# --------------------------------------------------------------------------- #
# Detail
# --------------------------------------------------------------------------- #


async def _detail(session: AsyncSession, company: Company, user: User) -> LeadDetailOut:
    state = await leads_service.get_state(session, company.id)
    reviews = await _reviews_for(session, [company.id])
    by_field = reviews.get(company.id, {})

    events = (
        (
            await session.execute(
                select(LeadEvent)
                .where(LeadEvent.company_id == company.id)
                .order_by(LeadEvent.created_at.desc(), LeadEvent.id.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )

    names = await _user_names_for(
        session,
        {e.actor_id for e in events}
        | {r.filled_by_id for r in by_field.values()}
        | {state.assigned_to_id if state else None},
    )

    unset = [f for f in REVIEW_FIELDS if by_field.get(f) is None or by_field[f].available is None]
    eff_status = leads_service.effective_status(state)
    assignee_id = leads_service.effective_assignee(state)

    return LeadDetailOut(
        id=company.id,
        name=company.name,
        category=company.category,
        address=company.address,
        phone=company.phone,
        email=company.email,
        website=company.website,
        source=company.source,
        source_url=company.source_url,
        status=eff_status,
        assignee_id=assignee_id,
        assignee_name=names.get(assignee_id),
        assigned_at=state.assigned_at if state else None,
        last_activity_at=state.last_activity_at if state else None,
        fields=[
            LeadFieldOut(
                field=f,
                available=by_field[f].available if f in by_field else None,
                comment=by_field[f].comment if f in by_field else None,
                filled_by=names.get(by_field[f].filled_by_id) if f in by_field else None,
                filled_at=by_field[f].filled_at if f in by_field else None,
            )
            for f in REVIEW_FIELDS
        ],
        events=[
            LeadEventOut(
                id=e.id,
                type=e.type,
                actor=names.get(e.actor_id),
                from_status=e.from_status,
                to_status=e.to_status,
                note=e.note,
                created_at=e.created_at,
            )
            for e in events
        ],
        available_actions=leads_service.available_actions(state, user, unset_fields=unset),
    )


async def _company_or_404(session: AsyncSession, company_id: int, user: User) -> Company:
    await leads_service.visible_to(session, company_id, user)  # raises LeadNotFound
    return await session.get(Company, company_id)


@router.get("/{company_id}", response_model=LeadDetailOut)
async def get_lead(
    company_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    company = await _company_or_404(session, company_id, user)
    return await _detail(session, company, user)


# --------------------------------------------------------------------------- #
# Transitions
# --------------------------------------------------------------------------- #


@router.post("/{company_id}/start", response_model=LeadDetailOut)
async def start_lead(
    company_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    await leads_service.claim(session, company_id, user)
    await session.commit()
    await _broadcast(company_id, STATUS_IN_PROGRESS)
    company = await session.get(Company, company_id)
    return await _detail(session, company, user)


@router.post("/{company_id}/switch", response_model=LeadDetailOut)
async def switch_lead(
    company_id: int,
    body: SwitchIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    """Drop one lead and pick up another in a single transaction (NFR-3).

    Nothing commits until both halves succeed, so a failed claim on the new lead
    cannot leave the operator having given up the old one for nothing.
    """
    await leads_service.switch(
        session, from_company_id=body.from_company_id, to_company_id=company_id, user=user, note=body.note
    )
    await session.commit()
    await _broadcast(body.from_company_id, STATUS_WAITING)
    await _broadcast(company_id, STATUS_IN_PROGRESS)
    company = await session.get(Company, company_id)
    return await _detail(session, company, user)


@router.post("/{company_id}/pause", response_model=LeadDetailOut)
async def pause_lead(
    company_id: int,
    body: NoteIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    await leads_service.pause(session, company_id, user, note=body.note)
    await session.commit()
    await _broadcast(company_id, STATUS_WAITING)
    company = await session.get(Company, company_id)
    return await _detail(session, company, user)


@router.post("/{company_id}/finish", response_model=LeadDetailOut)
async def finish_lead(
    company_id: int,
    body: FinishIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    state = await leads_service.finish(session, company_id, user, result=body.result, note=body.note)
    await session.commit()
    await _broadcast(company_id, state.status)
    company = await session.get(Company, company_id)
    return await _detail(session, company, user)


@router.post("/{company_id}/reopen", response_model=LeadDetailOut)
async def reopen_lead(
    company_id: int,
    body: NoteIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    await leads_service.reopen(session, company_id, user, note=body.note)
    await session.commit()
    await _broadcast(company_id, STATUS_IN_PROGRESS)
    company = await session.get(Company, company_id)
    return await _detail(session, company, user)


@router.post("/{company_id}/comment", response_model=LeadDetailOut)
async def comment_lead(
    company_id: int,
    body: NoteIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    await leads_service.comment(session, company_id, user, note=body.note)
    await session.commit()
    company = await session.get(Company, company_id)
    return await _detail(session, company, user)


@router.patch("/{company_id}/draft", response_model=dict)
async def save_draft(
    company_id: int,
    body: DraftIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Autosave. Never changes status, never writes a timeline row (FR-7)."""
    await leads_service.touch(session, company_id, user)
    fields = {k: v.model_dump() for k, v in {FIELD_WEBSITE: body.website, FIELD_LMS: body.lms}.items() if v is not None}
    if fields:
        await leads_service.save_draft(session, company_id, user, fields=fields)
    await session.commit()
    return {"saved_at": datetime.now(UTC).isoformat()}


# --------------------------------------------------------------------------- #
# Admin intervention
# --------------------------------------------------------------------------- #


@router.post("/{company_id}/release", response_model=LeadDetailOut)
async def admin_release_lead(
    company_id: int,
    body: NoteIn,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    state = await leads_service.get_state(session, company_id)
    previous_owner = state.assigned_to_id if state else None
    company = await session.get(Company, company_id)
    await leads_service.admin_release(session, company_id, admin, note=body.note)
    if previous_owner:
        await notify(
            session,
            user_id=previous_owner,
            message=f"Ishingiz bo'shatildi: {company.name}. Sabab: {(body.note or '').strip()}",
            link=f"lead:{company_id}",
        )
    await session.commit()
    await _broadcast(company_id, STATUS_WAITING)
    return await _detail(session, company, admin)


@router.post("/{company_id}/assign", response_model=LeadDetailOut)
async def admin_assign_lead(
    company_id: int,
    body: AssignIn,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> LeadDetailOut:
    company = await session.get(Company, company_id)
    await leads_service.admin_assign(session, company_id, admin, operator_id=body.operator_id, note=body.note)
    await notify(
        session,
        user_id=body.operator_id,
        message=f"Sizga yangi ish biriktirildi: {company.name}",
        link=f"lead:{company_id}",
    )
    await session.commit()
    await _broadcast(company_id, STATUS_IN_PROGRESS)
    return await _detail(session, company, admin)
