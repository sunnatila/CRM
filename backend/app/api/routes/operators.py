from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.models.company import Company
from app.models.lead import STATUS_APPROVED, STATUS_REJECTED, LeadState
from app.models.user import User
from app.schemas.auth import CreateOperatorRequest, UserOut
from app.schemas.stats import OperatorStatsOut, OverviewStatsOut

router = APIRouter(tags=["operators"])


def _period_starts() -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start, today_start - timedelta(days=now.weekday())


async def _counts_for(session: AsyncSession, user_id: int) -> tuple[int, int, int]:
    """Finished leads credited to this operator.

    Counted off `lead_states` -- the same source the profile's "So'nggi
    yakunlanganlar" table reads via `/leads?actor=me` -- so the number and the
    list under it can never disagree. They did: the counter used to require a
    `finish` *event* authored by the operator, while the table asked who last
    acted on the lead. Leads carried over by the v1->v2 migration have
    `type='migration'` with a NULL actor, so they appeared in the table while the
    counter above them read 0, and an operator saw their own finished work
    reported as nothing.

    v1 counted filled review rows, which would count drafts too; that is still
    excluded -- only a lead that actually reached approved/rejected counts.
    """
    today_start, week_start = _period_starts()
    base = select(func.count()).where(
        LeadState.status.in_([STATUS_APPROVED, STATUS_REJECTED]),
        LeadState.last_actor_id == user_id,
    )
    total = (await session.execute(base)).scalar_one()
    today = (await session.execute(base.where(LeadState.last_activity_at >= today_start))).scalar_one()
    week = (await session.execute(base.where(LeadState.last_activity_at >= week_start))).scalar_one()
    return today, week, total


@router.post("/operators", response_model=UserOut)
async def create_operator(
    body: CreateOperatorRequest,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> User:
    existing = (await session.execute(select(User).where(User.username == body.username))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="username already taken")

    operator = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role="operator",
    )
    session.add(operator)
    await session.commit()
    await session.refresh(operator)
    return operator


@router.get("/me/stats", response_model=OperatorStatsOut)
async def get_my_stats(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OperatorStatsOut:
    today, week, total = await _counts_for(session, user.id)
    return OperatorStatsOut(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        today_count=today,
        week_count=week,
        total_count=total,
    )


@router.get("/operators", response_model=list[OperatorStatsOut])
async def list_operators(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> list[OperatorStatsOut]:
    operators = (await session.execute(select(User).where(User.role == "operator"))).scalars().all()
    out = []
    for op in operators:
        today, week, total = await _counts_for(session, op.id)
        out.append(
            OperatorStatsOut(
                id=op.id,
                username=op.username,
                full_name=op.full_name,
                avatar_url=op.avatar_url,
                today_count=today,
                week_count=week,
                total_count=total,
            )
        )
    return out


@router.get("/operators/{operator_id}", response_model=OperatorStatsOut)
async def get_operator(
    operator_id: int,
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> OperatorStatsOut:
    op = await session.get(User, operator_id)
    if op is None or op.role != "operator":
        raise HTTPException(status_code=404, detail="operator not found")
    today, week, total = await _counts_for(session, op.id)
    return OperatorStatsOut(
        id=op.id,
        username=op.username,
        full_name=op.full_name,
        avatar_url=op.avatar_url,
        today_count=today,
        week_count=week,
        total_count=total,
    )


@router.get("/stats/overview", response_model=OverviewStatsOut)
async def get_overview_stats(
    _admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> OverviewStatsOut:
    today_start, week_start = _period_starts()

    # Same source as `_counts_for`, so the team totals here and the per-operator
    # numbers on the scoreboard below can never tell different stories.
    finished = select(func.count()).where(LeadState.status.in_([STATUS_APPROVED, STATUS_REJECTED]))
    today_filled = (await session.execute(finished.where(LeadState.last_activity_at >= today_start))).scalar_one()
    week_filled = (await session.execute(finished.where(LeadState.last_activity_at >= week_start))).scalar_one()
    # Deliberately NOT a "waiting" count. The dashboard's status-distribution row
    # already shows waiting, computed from the *effective* status; this endpoint
    # counted the literal column, so the same word showed two different numbers a
    # few pixels apart and an admin who noticed stopped trusting the whole page.
    # One number, one definition, one owner -- and this slot now answers what the
    # distribution row cannot: how much of the catalog has been dealt with at all.
    total_companies = (await session.execute(select(func.count()).select_from(Company))).scalar_one()
    finished_leads = (
        await session.execute(
            select(func.count()).where(LeadState.status.in_([STATUS_APPROVED, STATUS_REJECTED]))
        )
    ).scalar_one()
    active_operators = (
        await session.execute(select(func.count()).where(User.role == "operator", User.is_active))
    ).scalar_one()

    return OverviewStatsOut(
        today_filled=today_filled,
        week_filled=week_filled,
        total_companies=total_companies,
        finished_leads=finished_leads,
        active_operators=active_operators,
    )
