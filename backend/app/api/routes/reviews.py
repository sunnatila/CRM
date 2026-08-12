from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import any_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.claim import STATUS_ACTIVE, STATUS_DEFERRED, CompanyClaim
from app.models.company import Company
from app.models.permission_request import STATUS_PENDING, PermissionRequest
from app.models.review import FIELD_LMS, FIELD_WEBSITE, REVIEW_FIELDS, CompanyReview
from app.models.user import User
from app.schemas.review import (
    CompanyQueueItemOut,
    CompanyReviewDetailOut,
    PermissionRequestIn,
    PermissionRequestOut,
    ReviewFieldOut,
    ReviewSubmitIn,
)
from app.services import claims as claims_service
from app.services.notifications import notify

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _field_status(review: CompanyReview | None) -> str:
    if review is None or review.available is None:
        return "pending"
    return "confirmed" if review.available else "absent"


@router.get("", response_model=list[CompanyQueueItemOut])
async def list_reviews(
    status: str = Query(default="unfilled", pattern="^(unfilled|filled)$"),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    mine: bool = Query(default=False, description="filled status only: restrict to companies I filled"),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CompanyQueueItemOut]:
    reviewed_ids = select(CompanyReview.company_id).distinct()
    claimed_ids = select(CompanyClaim.company_id).where(CompanyClaim.status.in_([STATUS_ACTIVE, STATUS_DEFERRED]))
    mine_ids = select(CompanyReview.company_id).where(CompanyReview.filled_by_id == user.id).distinct()
    stmt = select(Company)
    if status == "unfilled":
        # AD-11: a company someone else (or the same operator) has claimed is not
        # up for grabs -- it only reappears here if that claim completes/releases.
        stmt = stmt.where(Company.id.not_in(reviewed_ids), Company.id.not_in(claimed_ids))
    else:
        stmt = stmt.where(Company.id.in_(reviewed_ids))
        if mine:
            stmt = stmt.where(Company.id.in_(mine_ids))
    if q:
        stmt = stmt.where(Company.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(category == any_(func.string_to_array(Company.category, "; ")))
    stmt = stmt.order_by(Company.id).limit(limit).offset(offset)

    companies = list((await session.execute(stmt)).scalars().all())
    if not companies:
        return []

    company_ids = [c.id for c in companies]
    reviews = (
        (await session.execute(select(CompanyReview).where(CompanyReview.company_id.in_(company_ids))))
        .scalars()
        .all()
    )
    by_company: dict[int, dict[str, CompanyReview]] = {}
    for r in reviews:
        by_company.setdefault(r.company_id, {})[r.field] = r

    return [
        CompanyQueueItemOut(
            id=c.id,
            name=c.name,
            category=c.category,
            address=c.address,
            phone=c.phone,
            source=c.source,
            website_status=_field_status(by_company.get(c.id, {}).get(FIELD_WEBSITE)),
            lms_status=_field_status(by_company.get(c.id, {}).get(FIELD_LMS)),
        )
        for c in companies
    ]


@router.get("/count", response_model=dict[str, int])
async def count_reviews(
    status: str = Query(default="unfilled", pattern="^(unfilled|filled)$"),
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    mine: bool = Query(default=False),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    reviewed_ids = select(CompanyReview.company_id).distinct()
    claimed_ids = select(CompanyClaim.company_id).where(CompanyClaim.status.in_([STATUS_ACTIVE, STATUS_DEFERRED]))
    mine_ids = select(CompanyReview.company_id).where(CompanyReview.filled_by_id == user.id).distinct()
    stmt = select(func.count()).select_from(Company)
    if status == "unfilled":
        stmt = stmt.where(Company.id.not_in(reviewed_ids), Company.id.not_in(claimed_ids))
    else:
        stmt = stmt.where(Company.id.in_(reviewed_ids))
        if mine:
            stmt = stmt.where(Company.id.in_(mine_ids))
    if q:
        stmt = stmt.where(Company.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(category == any_(func.string_to_array(Company.category, "; ")))
    total = (await session.execute(stmt)).scalar_one()
    return {"total": total}


@router.get("/categories", response_model=list[str])
async def list_categories(session: AsyncSession = Depends(get_session)) -> list[str]:
    rows = (await session.execute(select(Company.category).where(Company.category.isnot(None)))).scalars().all()
    tags: set[str] = set()
    for raw in rows:
        for tag in raw.split("; "):
            tag = tag.strip()
            if tag:
                tags.add(tag)
    return sorted(tags)


async def _load_detail(session: AsyncSession, company: Company) -> CompanyReviewDetailOut:
    reviews = (
        (await session.execute(select(CompanyReview).where(CompanyReview.company_id == company.id)))
        .scalars()
        .all()
    )
    by_field = {r.field: r for r in reviews}

    review_ids = [r.id for r in reviews]
    pending_review_ids: set[int] = set()
    if review_ids:
        pending_review_ids = set(
            (
                await session.execute(
                    select(PermissionRequest.review_id).where(
                        PermissionRequest.review_id.in_(review_ids),
                        PermissionRequest.status == STATUS_PENDING,
                    )
                )
            )
            .scalars()
            .all()
        )

    fields = []
    for field in REVIEW_FIELDS:
        r = by_field.get(field)
        filled_by_name = None
        if r is not None and r.filled_by_id is not None:
            filler = await session.get(User, r.filled_by_id)
            filled_by_name = filler.full_name if filler else None
        fields.append(
            ReviewFieldOut(
                field=field,
                available=r.available if r else None,
                comment=r.comment if r else None,
                filled_by=filled_by_name,
                filled_at=r.filled_at if r else None,
                locked=r.locked if r else False,
                pending_request=(r is not None and r.id in pending_review_ids),
            )
        )

    return CompanyReviewDetailOut(
        id=company.id,
        name=company.name,
        category=company.category,
        address=company.address,
        phone=company.phone,
        email=company.email,
        source=company.source,
        fields=fields,
    )


@router.get("/{company_id}", response_model=CompanyReviewDetailOut)
async def get_review(company_id: int, session: AsyncSession = Depends(get_session)) -> CompanyReviewDetailOut:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")
    return await _load_detail(session, company)


@router.post("/{company_id}", response_model=CompanyReviewDetailOut)
async def submit_review(
    company_id: int,
    body: ReviewSubmitIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CompanyReviewDetailOut:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    existing = (
        (await session.execute(select(CompanyReview).where(CompanyReview.company_id == company_id)))
        .scalars()
        .all()
    )
    by_field = {r.field: r for r in existing}

    submitted = {FIELD_WEBSITE: body.website, FIELD_LMS: body.lms}
    if not any(submitted.values()):
        raise HTTPException(status_code=400, detail="submit at least one field (website and/or lms)")

    already_locked = [f for f, data in submitted.items() if data is not None and by_field.get(f) and by_field[f].locked]
    if already_locked:
        raise HTTPException(status_code=409, detail=f"already reviewed and locked: {', '.join(already_locked)}")

    now = datetime.now(UTC)
    for field, data in submitted.items():
        if data is None:
            continue
        row = by_field.get(field)
        if row is None:
            row = CompanyReview(company_id=company_id, field=field)
            session.add(row)
        row.available = data.available
        row.comment = data.comment
        row.filled_by_id = user.id
        row.filled_at = now
        row.locked = True

    submitted_fields = {f for f, d in submitted.items() if d is not None}
    fully_reviewed = all(
        f in submitted_fields or (by_field.get(f) is not None and by_field[f].locked) for f in REVIEW_FIELDS
    )
    if fully_reviewed:
        # AD-11: a completed review retires the claim -- it stops counting toward
        # this operator's active/deferred state (and toward overdue blocking).
        await claims_service.complete_claims_for(session, company_id=company_id, operator_id=user.id)

    await session.commit()
    return await _load_detail(session, company)


@router.post("/{company_id}/{field}/request-permission", response_model=PermissionRequestOut)
async def request_permission(
    company_id: int,
    field: str,
    body: PermissionRequestIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PermissionRequestOut:
    if field not in REVIEW_FIELDS:
        raise HTTPException(status_code=404, detail=f"unknown field, expected one of {REVIEW_FIELDS}")

    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    review = (
        await session.execute(
            select(CompanyReview).where(CompanyReview.company_id == company_id, CompanyReview.field == field)
        )
    ).scalar_one_or_none()
    if review is None or not review.locked:
        raise HTTPException(status_code=400, detail="this field is not locked -- nothing to request")

    already_pending = (
        await session.execute(
            select(PermissionRequest).where(
                PermissionRequest.review_id == review.id, PermissionRequest.status == STATUS_PENDING
            )
        )
    ).scalar_one_or_none()
    if already_pending is not None:
        raise HTTPException(status_code=409, detail="a permission request for this field is already pending")

    request = PermissionRequest(review_id=review.id, requested_by_id=user.id, reason=body.reason)
    session.add(request)
    await session.flush()

    admin_ids = (await session.execute(select(User.id).where(User.role == "admin", User.is_active))).scalars().all()
    for admin_id in admin_ids:
        await notify(
            session,
            user_id=admin_id,
            message=f"{user.full_name} ruxsat so'radi: {company.name} — {field}",
            link=f"permission-request:{request.id}",
        )

    await session.commit()
    return PermissionRequestOut(
        id=request.id,
        review_id=review.id,
        company_id=company_id,
        company_name=company.name,
        field=field,
        requested_by=user.full_name,
        reason=request.reason,
        status=request.status,
        created_at=request.created_at,
        resolved_at=request.resolved_at,
        resolution_note=request.resolution_note,
    )
