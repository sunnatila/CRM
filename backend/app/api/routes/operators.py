from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_admin
from app.core.security import hash_password
from app.models.permission_request import STATUS_PENDING, PermissionRequest
from app.models.review import FIELD_WEBSITE, CompanyReview
from app.models.user import User
from app.schemas.auth import CreateOperatorRequest, UserOut
from app.schemas.review import OperatorStatsOut, OverviewStatsOut

router = APIRouter(tags=["operators"])


async def _counts_for(session: AsyncSession, user_id: int) -> tuple[int, int, int]:
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())

    base = select(func.count()).where(CompanyReview.field == FIELD_WEBSITE, CompanyReview.filled_by_id == user_id)
    total = (await session.execute(base)).scalar_one()
    today = (await session.execute(base.where(CompanyReview.filled_at >= today_start))).scalar_one()
    week = (await session.execute(base.where(CompanyReview.filled_at >= week_start))).scalar_one()
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
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())

    base = select(func.count()).where(CompanyReview.field == FIELD_WEBSITE)
    today_filled = (await session.execute(base.where(CompanyReview.filled_at >= today_start))).scalar_one()
    week_filled = (await session.execute(base.where(CompanyReview.filled_at >= week_start))).scalar_one()
    pending_requests = (
        await session.execute(select(func.count()).where(PermissionRequest.status == STATUS_PENDING))
    ).scalar_one()
    active_operators = (
        await session.execute(select(func.count()).where(User.role == "operator", User.is_active))
    ).scalar_one()

    return OverviewStatsOut(
        today_filled=today_filled,
        week_filled=week_filled,
        pending_requests=pending_requests,
        active_operators=active_operators,
    )
