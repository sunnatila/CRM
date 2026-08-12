from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models.claim import CompanyClaim
from app.models.company import Company
from app.models.user import User
from app.schemas.claim import ClaimOut, ClaimRequestOut, DeferClaimIn, DeferResultOut, MyClaimsOut, ReleaseClaimIn
from app.services import claims as claims_service
from app.services.notifications import notify

router = APIRouter(prefix="/claims", tags=["claims"])


class RequestExtendIn(BaseModel):
    days: int
    reason: str


async def _notify_admins_of_request(session: AsyncSession, *, message: str, link: str) -> None:
    admin_ids = (await session.execute(select(User.id).where(User.role == "admin", User.is_active))).scalars().all()
    for admin_id in admin_ids:
        await notify(session, user_id=admin_id, message=message, link=link)


@router.get("/me", response_model=MyClaimsOut)
async def get_my_claims(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MyClaimsOut:
    active = await claims_service.get_active_claim(session, user.id)
    deferred = await claims_service.get_deferred_claims(session, user.id)
    return MyClaimsOut(
        active=await claims_service.to_claim_out(session, active) if active else None,
        deferred=[await claims_service.to_claim_out(session, c) for c in deferred],
    )


@router.post("/{company_id}/claim", response_model=ClaimOut)
async def claim_company(
    company_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ClaimOut:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="company not found")

    try:
        claim = await claims_service.claim_company(session, user.id, company_id)
    except claims_service.OverdueClaimsBlock as exc:
        overdue_out = [await claims_service.to_claim_out(session, c) for c in exc.claims]
        raise HTTPException(
            status_code=409,
            detail={
                "code": "overdue",
                "message": "Muddati o'tgan ishlaringiz bor -- avval ularni hal qiling.",
                "claims": [c.model_dump(mode="json") for c in overdue_out],
            },
        ) from exc
    except claims_service.ActiveClaimExists as exc:
        active_out = await claims_service.to_claim_out(session, exc.claim)
        raise HTTPException(
            status_code=409,
            detail={
                "code": "active_claim_exists",
                "message": f"Sizda faol ish bor: {active_out.company_name}.",
                "active_claim": active_out.model_dump(mode="json"),
            },
        ) from exc
    except claims_service.CompanyAlreadyClaimed as exc:
        raise HTTPException(status_code=409, detail={"code": "already_claimed"}) from exc

    await session.commit()
    return await claims_service.to_claim_out(session, claim)


async def _get_owned_claim(session: AsyncSession, claim_id: int, user: User) -> CompanyClaim:
    claim = await session.get(CompanyClaim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="claim not found")
    if claim.operator_id != user.id:
        raise HTTPException(status_code=403, detail="not your claim")
    return claim


@router.post("/{claim_id}/defer", response_model=DeferResultOut)
async def defer_claim(
    claim_id: int,
    body: DeferClaimIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DeferResultOut:
    claim = await _get_owned_claim(session, claim_id, user)
    auto_approved, request = await claims_service.defer_claim(session, claim, days=body.days, reason=body.reason)

    if not auto_approved and request is not None:
        company = await session.get(Company, claim.company_id)
        await _notify_admins_of_request(
            session,
            message=f"{user.full_name} muddat cho'zishni so'radi: {company.name} ({body.days} kun)",
            link=f"claim-request:{request.id}",
        )

    await session.commit()
    return DeferResultOut(
        auto_approved=auto_approved,
        claim=await claims_service.to_claim_out(session, claim) if auto_approved else None,
        claim_request_id=request.id if request else None,
    )


@router.post("/{claim_id}/request-extend", response_model=ClaimRequestOut)
async def request_extend(
    claim_id: int,
    body: RequestExtendIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ClaimRequestOut:
    claim = await _get_owned_claim(session, claim_id, user)
    request = await claims_service.request_extend(session, claim, days=body.days, reason=body.reason)

    company = await session.get(Company, claim.company_id)
    await _notify_admins_of_request(
        session,
        message=f"{user.full_name} muddat cho'zishni so'radi: {company.name} ({body.days} kun)",
        link=f"claim-request:{request.id}",
    )
    await session.commit()

    return ClaimRequestOut(
        id=request.id,
        claim_id=claim.id,
        company_id=claim.company_id,
        company_name=company.name,
        operator_id=user.id,
        operator_name=user.full_name,
        action=request.action,
        requested_days=request.requested_days,
        reason=request.reason,
        status=request.status,
        created_at=request.created_at,
        resolved_at=request.resolved_at,
        resolution_note=request.resolution_note,
    )


@router.post("/{claim_id}/request-release", response_model=ClaimRequestOut)
async def request_release(
    claim_id: int,
    body: ReleaseClaimIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ClaimRequestOut:
    claim = await _get_owned_claim(session, claim_id, user)
    request = await claims_service.request_release(session, claim, reason=body.reason)

    company = await session.get(Company, claim.company_id)
    await _notify_admins_of_request(
        session,
        message=f"{user.full_name} ishdan voz kechishni so'radi: {company.name}",
        link=f"claim-request:{request.id}",
    )
    await session.commit()

    return ClaimRequestOut(
        id=request.id,
        claim_id=claim.id,
        company_id=claim.company_id,
        company_name=company.name,
        operator_id=user.id,
        operator_name=user.full_name,
        action=request.action,
        requested_days=request.requested_days,
        reason=request.reason,
        status=request.status,
        created_at=request.created_at,
        resolved_at=request.resolved_at,
        resolution_note=request.resolution_note,
    )
