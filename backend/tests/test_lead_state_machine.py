"""The rules v2 actually promises, as tests.

Grouped by the promise each one protects rather than by function, so a failure
names the broken behaviour and not just the broken call.
"""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.lead import (
    EVENT_AUTO_RELEASE,
    EVENT_HANDOVER,
    STATUS_APPROVED,
    STATUS_IN_PROGRESS,
    STATUS_NEW,
    STATUS_REJECTED,
    STATUS_WAITING,
    LeadEvent,
    LeadState,
)
from app.services import leads as svc
from tests.conftest import make_company, make_user, set_fields


# --------------------------------------------------------------------------- #
# Two operators never work the same lead (FR-3, FR-4, NFR-4)
# --------------------------------------------------------------------------- #


async def test_claim_makes_lead_in_progress_and_assigns_it(session):
    op = await make_user(session, "malika")
    company = await make_company(session)

    state = await svc.claim(session, company.id, op)

    assert state.status == STATUS_IN_PROGRESS
    assert state.assigned_to_id == op.id


async def test_second_operator_cannot_claim_a_held_lead(session):
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    company = await make_company(session)

    await svc.claim(session, company.id, malika)

    with pytest.raises(svc.LeadError) as exc:
        await svc.claim(session, company.id, bekzod)
    assert exc.value.code == "held_by_other"


async def test_concurrent_claims_produce_exactly_one_winner(session, session_factory):
    """The race the whole conditional upsert exists for.

    Two real sessions, two real connections, both claiming at once: the database
    decides, so exactly one succeeds no matter how the interleaving falls.
    """
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    company = await make_company(session)
    await session.commit()

    async def attempt(user_id: int) -> bool:
        async with session_factory() as s:
            user = await s.get(type(malika), user_id)
            try:
                await svc.claim(s, company.id, user)
                await s.commit()
                return True
            except Exception:
                await s.rollback()
                return False

    results = await asyncio.gather(attempt(malika.id), attempt(bekzod.id))
    assert sum(results) == 1, "ikkita operator bir vaqtda bitta leadni oldi"


async def test_other_operators_in_progress_lead_is_invisible(session):
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    company = await make_company(session)
    await svc.claim(session, company.id, malika)

    # 404, not 403: the existence of the lead is itself withheld (FR-4).
    with pytest.raises(svc.LeadNotFound):
        await svc.visible_to(session, company.id, bekzod)

    # The admin exception.
    admin = await make_user(session, "aziz", role="admin")
    assert await svc.visible_to(session, company.id, admin) is not None


async def test_reclaiming_your_own_lead_is_a_no_op(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    first = await svc.claim(session, company.id, op)
    second = await svc.claim(session, company.id, op)
    assert first.id == second.id


# --------------------------------------------------------------------------- #
# Nobody walks away from unfinished work silently (FR-5, FR-6)
# --------------------------------------------------------------------------- #


async def test_pause_without_a_note_is_refused(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    await svc.claim(session, company.id, op)

    for empty in (None, "", "   "):
        with pytest.raises(svc.LeadError) as exc:
            await svc.pause(session, company.id, op, note=empty)
        assert exc.value.code == "note_required"


async def test_pause_records_the_handover_note_and_frees_the_lead(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    await svc.claim(session, company.id, op)

    state = await svc.pause(session, company.id, op, note="3 marta qo'ng'iroq qildim, javob yo'q")

    assert state.status == STATUS_WAITING
    assert state.assigned_to_id is None
    events = (
        (await session.execute(select(LeadEvent).where(LeadEvent.type == EVENT_HANDOVER))).scalars().all()
    )
    assert len(events) == 1
    assert "javob yo'q" in events[0].note


async def test_starting_a_second_lead_demands_a_handover(session):
    op = await make_user(session, "malika")
    first = await make_company(session, "Birinchi", "1")
    second = await make_company(session, "Ikkinchi", "2")
    await svc.claim(session, first.id, op)

    with pytest.raises(svc.LeadError) as exc:
        await svc.claim(session, second.id, op)
    assert exc.value.code == "handover_required"
    assert exc.value.context["active_company_id"] == first.id


async def test_switch_moves_both_leads_in_one_step(session):
    op = await make_user(session, "malika")
    first = await make_company(session, "Birinchi", "1")
    second = await make_company(session, "Ikkinchi", "2")
    await svc.claim(session, first.id, op)

    await svc.switch(session, from_company_id=first.id, to_company_id=second.id, user=op, note="ertalab qayta")

    assert (await svc.get_state(session, first.id)).status == STATUS_WAITING
    assert (await svc.get_state(session, second.id)).status == STATUS_IN_PROGRESS


async def test_switch_without_a_note_leaves_the_original_lead_untouched(session):
    """NFR-3: an operator must never end up having dropped one lead and gained
    nothing."""
    op = await make_user(session, "malika")
    first = await make_company(session, "Birinchi", "1")
    second = await make_company(session, "Ikkinchi", "2")
    await svc.claim(session, first.id, op)

    with pytest.raises(svc.LeadError):
        await svc.switch(session, from_company_id=first.id, to_company_id=second.id, user=op, note="  ")

    assert (await svc.get_state(session, first.id)).status == STATUS_IN_PROGRESS
    assert await svc.get_state(session, second.id) is None


# --------------------------------------------------------------------------- #
# A forgotten lead comes back to the pool (FR-8)
# --------------------------------------------------------------------------- #


async def test_lead_untouched_for_four_hours_reads_as_waiting(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    state = await svc.claim(session, company.id, op)

    state.last_activity_at = datetime.now(UTC) - timedelta(hours=svc.AUTO_RELEASE_HOURS, minutes=1)
    await session.flush()

    assert svc.is_stale(state)
    assert svc.effective_status(state) == STATUS_WAITING
    assert svc.effective_assignee(state) is None


async def test_a_stale_lead_can_be_taken_over_and_the_takeover_is_recorded(session):
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    company = await make_company(session)
    state = await svc.claim(session, company.id, malika)
    state.last_activity_at = datetime.now(UTC) - timedelta(hours=5)
    await session.flush()

    taken = await svc.claim(session, company.id, bekzod)

    assert taken.assigned_to_id == bekzod.id
    released = (
        (await session.execute(select(LeadEvent).where(LeadEvent.type == EVENT_AUTO_RELEASE))).scalars().all()
    )
    assert len(released) == 1, "avtomatik bo'shatish tarixga yozilmadi"


async def test_a_stale_lead_does_not_block_its_own_owner(session):
    """v1's exact failure mode, inverted: a lead you forgot about four hours ago
    must not stand between you and your next piece of work."""
    op = await make_user(session, "malika")
    forgotten = await make_company(session, "Unutilgan", "1")
    fresh = await make_company(session, "Yangi", "2")
    state = await svc.claim(session, forgotten.id, op)
    state.last_activity_at = datetime.now(UTC) - timedelta(hours=6)
    await session.flush()

    taken = await svc.claim(session, fresh.id, op)  # no handover_required
    assert taken.status == STATUS_IN_PROGRESS


async def test_a_draft_save_pushes_the_release_clock_back(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    state = await svc.claim(session, company.id, op)
    state.last_activity_at = datetime.now(UTC) - timedelta(hours=3, minutes=59)
    await session.flush()

    await svc.touch(session, company.id, op)
    assert not svc.is_stale(await svc.get_state(session, company.id))


# --------------------------------------------------------------------------- #
# Finishing and correcting (FR-9, FR-10, FR-19)
# --------------------------------------------------------------------------- #


async def test_approve_requires_both_fields_to_be_decided(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    await svc.claim(session, company.id, op)
    await set_fields(session, company.id, website=True, lms=None)

    with pytest.raises(svc.LeadError) as exc:
        await svc.finish(session, company.id, op, result=STATUS_APPROVED, note=None)
    assert exc.value.code == "fields_incomplete"
    assert exc.value.context["missing"] == ["lms"]


async def test_approve_succeeds_once_both_fields_are_decided(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    await svc.claim(session, company.id, op)
    # "yo'q" counts as decided -- absence is a finding, not a blank.
    await set_fields(session, company.id, website=True, lms=False)

    state = await svc.finish(session, company.id, op, result=STATUS_APPROVED, note=None)
    assert state.status == STATUS_APPROVED
    assert state.assigned_to_id is None


async def test_reject_needs_a_reason_but_not_the_fields(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    await svc.claim(session, company.id, op)

    with pytest.raises(svc.LeadError) as exc:
        await svc.finish(session, company.id, op, result=STATUS_REJECTED, note=None)
    assert exc.value.code == "note_required"

    state = await svc.finish(session, company.id, op, result=STATUS_REJECTED, note="raqam ishlamaydi")
    assert state.status == STATUS_REJECTED


async def test_reopen_needs_a_reason_and_keeps_the_data(session):
    op = await make_user(session, "malika")
    company = await make_company(session)
    await svc.claim(session, company.id, op)
    await set_fields(session, company.id, website=True, lms=True)
    await svc.finish(session, company.id, op, result=STATUS_APPROVED, note=None)

    with pytest.raises(svc.LeadError):
        await svc.reopen(session, company.id, op, note="")

    state = await svc.reopen(session, company.id, op, note="LMS ni xato belgilabman")
    assert state.status == STATUS_IN_PROGRESS
    assert state.assigned_to_id == op.id
    assert await svc._unset_fields(session, company.id) == []  # nothing was wiped


async def test_reopening_is_open_to_any_operator_no_admin_needed(session):
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    company = await make_company(session)
    await svc.claim(session, company.id, malika)
    await set_fields(session, company.id, website=True, lms=True)
    await svc.finish(session, company.id, malika, result=STATUS_APPROVED, note=None)

    state = await svc.reopen(session, company.id, bekzod, note="tekshirib ko'ray")
    assert state.assigned_to_id == bekzod.id


# --------------------------------------------------------------------------- #
# The transition table is the only law (FR-2)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "pair",
    [
        (STATUS_NEW, STATUS_APPROVED),
        (STATUS_NEW, STATUS_REJECTED),
        (STATUS_WAITING, STATUS_APPROVED),
        (STATUS_APPROVED, STATUS_REJECTED),
        (STATUS_IN_PROGRESS, STATUS_NEW),
    ],
)
def test_forbidden_transitions_are_refused(pair):
    with pytest.raises(svc.LeadError) as exc:
        svc.check_transition(*pair)
    assert exc.value.code == "invalid_transition"


@pytest.mark.parametrize("pair", sorted(svc.ALLOWED_TRANSITIONS))
def test_allowed_transitions_pass(pair):
    svc.check_transition(*pair)


async def test_finishing_a_lead_you_do_not_hold_is_refused(session):
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    company = await make_company(session)
    await svc.claim(session, company.id, malika)
    await set_fields(session, company.id, website=True, lms=True)

    with pytest.raises(svc.LeadError) as exc:
        await svc.finish(session, company.id, bekzod, result=STATUS_APPROVED, note=None)
    assert exc.value.code == "held_by_other"


# --------------------------------------------------------------------------- #
# The timeline is the record (FR-11)
# --------------------------------------------------------------------------- #


async def test_untouched_company_reads_as_new_without_a_row(session):
    """AR-2: the scrape pipeline must be able to insert companies without the
    review domain writing anything."""
    company = await make_company(session)
    assert await svc.get_state(session, company.id) is None
    assert svc.effective_status(None) == STATUS_NEW


async def test_every_transition_leaves_a_timeline_entry(session):
    op = await make_user(session, "malika")
    company = await make_company(session)

    await svc.claim(session, company.id, op)
    await svc.pause(session, company.id, op, note="keyinroq")
    await svc.claim(session, company.id, op)
    await set_fields(session, company.id, website=True, lms=True)
    await svc.finish(session, company.id, op, result=STATUS_APPROVED, note=None)

    events = (
        (
            await session.execute(
                select(LeadEvent).where(LeadEvent.company_id == company.id).order_by(LeadEvent.id)
            )
        )
        .scalars()
        .all()
    )
    assert [e.to_status for e in events] == [
        STATUS_IN_PROGRESS,
        STATUS_WAITING,
        STATUS_IN_PROGRESS,
        STATUS_APPROVED,
    ]


async def test_admin_release_frees_the_lead_and_names_a_reason(session):
    malika = await make_user(session, "malika")
    admin = await make_user(session, "aziz", role="admin")
    company = await make_company(session)
    await svc.claim(session, company.id, malika)

    with pytest.raises(svc.LeadError):
        await svc.admin_release(session, company.id, admin, note=None)

    state = await svc.admin_release(session, company.id, admin, note="smena tugadi")
    assert state.status == STATUS_WAITING
    assert state.assigned_to_id is None


async def test_admin_assign_hands_a_lead_to_a_named_operator(session):
    bekzod = await make_user(session, "bekzod")
    admin = await make_user(session, "aziz", role="admin")
    company = await make_company(session)

    state = await svc.admin_assign(session, company.id, admin, operator_id=bekzod.id, note="sizga topshirdim")
    assert state.status == STATUS_IN_PROGRESS
    assert state.assigned_to_id == bekzod.id


# --------------------------------------------------------------------------- #
# Queue visibility (FR-14)
# --------------------------------------------------------------------------- #


async def test_queue_hides_other_peoples_work_from_operators_but_not_admins(session):
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    admin = await make_user(session, "aziz", role="admin")
    held = await make_company(session, "Band", "1")
    free = await make_company(session, "Bo'sh", "2")
    await svc.claim(session, held.id, malika)
    await session.flush()

    async def visible_names(user):
        rows = (await session.execute(svc.base_query(user))).all()
        return {row[0].name for row in rows}

    assert await visible_names(bekzod) == {"Bo'sh"}
    assert await visible_names(malika) == {"Band", "Bo'sh"}
    assert await visible_names(admin) == {"Band", "Bo'sh"}


async def test_available_actions_reflect_who_is_asking(session):
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    company = await make_company(session)

    assert "start" in svc.available_actions(None, malika)

    state = await svc.claim(session, company.id, malika)
    mine = svc.available_actions(state, malika, unset_fields=["lms"])
    assert "pause" in mine and "reject" in mine
    assert "approve" not in mine, "yarim to'ldirilgan lead tasdiqlanmasligi kerak"

    assert "approve" in svc.available_actions(state, malika, unset_fields=[])
    assert svc.available_actions(state, bekzod) == []


# --------------------------------------------------------------------------- #
# The admin supervises; the admin does not work leads
# --------------------------------------------------------------------------- #


async def test_admin_cannot_claim_a_lead(session):
    admin = await make_user(session, "aziz", role="admin")
    company = await make_company(session)

    with pytest.raises(svc.LeadError) as exc:
        await svc.claim(session, company.id, admin)
    assert exc.value.code == "admin_readonly"
    assert await svc.get_state(session, company.id) is None, "rad etilgan urinish qator yaratmasligi kerak"


async def test_admin_cannot_touch_a_lead_an_operator_holds(session):
    """Not even the lead's own workflow actions -- an admin who wants it moved
    releases it or reassigns it, both of which are recorded as interventions."""
    malika = await make_user(session, "malika")
    admin = await make_user(session, "aziz", role="admin")
    company = await make_company(session)
    await svc.claim(session, company.id, malika)
    await set_fields(session, company.id, website=True, lms=True)

    for call in (
        lambda: svc.pause(session, company.id, admin, note="men qoldiraman"),
        lambda: svc.comment(session, company.id, admin, note="izoh"),
        lambda: svc.finish(session, company.id, admin, result=STATUS_APPROVED, note=None),
        lambda: svc.touch(session, company.id, admin),
    ):
        with pytest.raises(svc.LeadError) as exc:
            await call()
        assert exc.value.code == "admin_readonly"

    assert (await svc.get_state(session, company.id)).assigned_to_id == malika.id


async def test_admin_cannot_reopen_a_finished_lead(session):
    malika = await make_user(session, "malika")
    admin = await make_user(session, "aziz", role="admin")
    company = await make_company(session)
    await svc.claim(session, company.id, malika)
    await set_fields(session, company.id, website=True, lms=True)
    await svc.finish(session, company.id, malika, result=STATUS_APPROVED, note=None)

    with pytest.raises(svc.LeadError) as exc:
        await svc.reopen(session, company.id, admin, note="qayta ko'ray")
    assert exc.value.code == "admin_readonly"
    assert (await svc.get_state(session, company.id)).status == STATUS_APPROVED


async def test_admin_actions_are_supervision_only(session):
    """What the action bar offers an admin: release or reassign, never work."""
    malika = await make_user(session, "malika")
    admin = await make_user(session, "aziz", role="admin")
    company = await make_company(session)

    free = svc.available_actions(None, admin)
    assert free == ["admin_assign"], free

    state = await svc.claim(session, company.id, malika)
    held = svc.available_actions(state, admin, unset_fields=[])
    assert held == ["admin_release"], held
    assert not {"start", "pause", "approve", "reject", "reopen", "comment"} & set(held)


async def test_admin_still_supervises(session):
    """The guard must not have taken away what the admin is actually for."""
    malika = await make_user(session, "malika")
    bekzod = await make_user(session, "bekzod")
    admin = await make_user(session, "aziz", role="admin")
    company = await make_company(session)
    await svc.claim(session, company.id, malika)

    assert await svc.visible_to(session, company.id, admin) is not None

    released = await svc.admin_release(session, company.id, admin, note="smena tugadi")
    assert released.status == STATUS_WAITING

    assigned = await svc.admin_assign(session, company.id, admin, operator_id=bekzod.id, note="sizga")
    assert assigned.assigned_to_id == bekzod.id
