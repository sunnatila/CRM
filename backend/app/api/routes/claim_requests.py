from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_admin
from app.models.claim import CompanyClaim
from app.models.claim_request import (
    ACTION_EXTEND,
    STATUS_APPROVED,
    STATUS_DENIED,
    STATUS_PENDING,
    ClaimRequest,
)
from app.models.company import Company
from app.models.user import User
from app.schemas.claim import ClaimRequestOut, ResolveClaimRequestIn
from app.services import claims as claims_service
from app.services.notifications import notify

router = APIRouter(prefix="/claim-requests", tags=["claim-requests"])


async def _to_out(session: AsyncSession, request: ClaimRequest) -> ClaimRequestOut:
    claim = await session.get(CompanyClaim, request.claim_id)
    company = await session.get(Company, claim.company_id) if claim else None
    operator = await session.get(User, request.operator_id)
    return ClaimRequestOut(
        id=request.id,
        claim_id=request.claim_id,
        company_id=claim.company_id if claim else 0,
        company_name=company.name if company else "",
        operator_id=request.operator_id,
        operator_name=operator.full_name if operator else "",
        action=request.action,
        requested_days=request.requested_days,
        reason=request.reason,
        status=request.status,
        created_at=request.created_at,
        resolved_at=request.resolved_at,
        resolution_note=request.resolution_note,
    )


@router.get("", response_model=list[ClaimRequestOut])
async def list_claim_requests(
    status: str | None = Query(default=None, pattern="^(pending|approved|denied)$"),
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ClaimRequestOut]:
    stmt = select(ClaimRequest).order_by(ClaimRequest.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(ClaimRequest.status == status)
    # Operators only ever see their own requests; admins see everyone's.
    if user.role != "admin":
        stmt = stmt.where(ClaimRequest.operator_id == user.id)
    requests = (await session.execute(stmt)).scalars().all()
    return [await _to_out(session, r) for r in requests]


@router.post("/{request_id}/approve", response_model=ClaimRequestOut)
async def approve_claim_request(
    request_id: int,
    body: ResolveClaimRequestIn = ResolveClaimRequestIn(),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ClaimRequestOut:
    request = await session.get(ClaimRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="claim request not found")
    if request.status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail="this request has already been resolved")

    claim = await session.get(CompanyClaim, request.claim_id)
    company = await session.get(Company, claim.company_id)

    if request.action == ACTION_EXTEND:
        await claims_service.resolve_extend(session, claim, days=request.requested_days or 1)
        message = f"Muddat cho'zish so'rovingiz tasdiqlandi: {company.name} ({request.requested_days} kun)"
    else:
        await claims_service.resolve_release(session, claim)
        message = f"Ishdan voz kechish so'rovingiz tasdiqlandi: {company.name}"

    request.status = STATUS_APPROVED
    request.resolved_at = datetime.now(UTC)
    request.resolved_by_id = admin.id
    request.resolution_note = body.note

    if body.note:
        message += f'. Izoh: "{body.note}"'
    await notify(session, user_id=request.operator_id, message=message, link=f"claim-request:{request.id}")

    await session.commit()
    return await _to_out(session, request)


@router.post("/{request_id}/deny", response_model=ClaimRequestOut)
async def deny_claim_request(
    request_id: int,
    body: ResolveClaimRequestIn = ResolveClaimRequestIn(),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> ClaimRequestOut:
    request = await session.get(ClaimRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="claim request not found")
    if request.status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail="this request has already been resolved")

    claim = await session.get(CompanyClaim, request.claim_id)
    company = await session.get(Company, claim.company_id)

    request.status = STATUS_DENIED
    request.resolved_at = datetime.now(UTC)
    request.resolved_by_id = admin.id
    request.resolution_note = body.note

    action_label = "Muddat cho'zish" if request.action == ACTION_EXTEND else "Ishdan voz kechish"
    message = f"{action_label} so'rovingiz rad etildi: {company.name}"
    if body.note:
        message += f'. Izoh: "{body.note}"'
    await notify(session, user_id=request.operator_id, message=message, link=f"claim-request:{request.id}")

    await session.commit()
    return await _to_out(session, request)
