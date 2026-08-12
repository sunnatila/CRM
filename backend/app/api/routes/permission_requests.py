from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_admin
from app.models.company import Company
from app.models.permission_request import STATUS_APPROVED, STATUS_DENIED, STATUS_PENDING, PermissionRequest
from app.models.review import CompanyReview
from app.models.user import User
from app.schemas.review import PermissionRequestOut, ResolvePermissionRequestIn
from app.services.notifications import notify

router = APIRouter(prefix="/permission-requests", tags=["permission-requests"])


async def _to_out(session: AsyncSession, request: PermissionRequest) -> PermissionRequestOut:
    review = await session.get(CompanyReview, request.review_id)
    company = await session.get(Company, review.company_id) if review else None
    requester = await session.get(User, request.requested_by_id)
    return PermissionRequestOut(
        id=request.id,
        review_id=request.review_id,
        company_id=review.company_id if review else 0,
        company_name=company.name if company else "",
        field=review.field if review else "",
        requested_by=requester.full_name if requester else "",
        reason=request.reason,
        status=request.status,
        created_at=request.created_at,
        resolved_at=request.resolved_at,
        resolution_note=request.resolution_note,
    )


@router.get("", response_model=list[PermissionRequestOut])
async def list_permission_requests(
    status: str | None = Query(default=None, pattern="^(pending|approved|denied)$"),
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PermissionRequestOut]:
    stmt = select(PermissionRequest).order_by(PermissionRequest.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(PermissionRequest.status == status)
    # Operators only ever see their own requests; admins see everyone's.
    if user.role != "admin":
        stmt = stmt.where(PermissionRequest.requested_by_id == user.id)
    requests = (await session.execute(stmt)).scalars().all()
    return [await _to_out(session, r) for r in requests]


@router.post("/{request_id}/approve", response_model=PermissionRequestOut)
async def approve_permission_request(
    request_id: int,
    body: ResolvePermissionRequestIn = ResolvePermissionRequestIn(),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PermissionRequestOut:
    request = await session.get(PermissionRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="permission request not found")
    if request.status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail="this request has already been resolved")

    review = await session.get(CompanyReview, request.review_id)
    review.locked = False

    request.status = STATUS_APPROVED
    request.resolved_at = datetime.now(UTC)
    request.resolved_by_id = admin.id
    request.resolution_note = body.note

    company = await session.get(Company, review.company_id)
    message = f"Ruxsatingiz tasdiqlandi: {company.name} — {review.field}"
    if body.note:
        message += f'. Izoh: "{body.note}"'
    await notify(
        session,
        user_id=request.requested_by_id,
        message=message,
        link=f"review:{review.company_id}:{review.field}",
    )

    await session.commit()
    return await _to_out(session, request)


@router.post("/{request_id}/deny", response_model=PermissionRequestOut)
async def deny_permission_request(
    request_id: int,
    body: ResolvePermissionRequestIn = ResolvePermissionRequestIn(),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PermissionRequestOut:
    request = await session.get(PermissionRequest, request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="permission request not found")
    if request.status != STATUS_PENDING:
        raise HTTPException(status_code=409, detail="this request has already been resolved")

    review = await session.get(CompanyReview, request.review_id)
    request.status = STATUS_DENIED
    request.resolved_at = datetime.now(UTC)
    request.resolved_by_id = admin.id
    request.resolution_note = body.note

    company = await session.get(Company, review.company_id)
    message = f"Ruxsat so'rovingiz rad etildi: {company.name} — {review.field}"
    if body.note:
        message += f'. Izoh: "{body.note}"'
    await notify(
        session,
        user_id=request.requested_by_id,
        message=message,
        link=f"review:{review.company_id}:{review.field}",
    )

    await session.commit()
    return await _to_out(session, request)
