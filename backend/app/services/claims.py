"""AD-11: one operator works one company (the 'active' claim) at a time.

Moving to a different company while the active one is unfinished requires
committing to a deadline for it (auto-approved at <= AUTO_APPROVE_MAX_DAYS,
otherwise an admin-approved ClaimRequest). A deferred claim whose deadline has
passed blocks the operator from claiming anything new until they resolve it
(extend or release, both via ClaimRequest -- release always needs approval).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claim import STATUS_ACTIVE, STATUS_COMPLETED, STATUS_DEFERRED, STATUS_RELEASED, CompanyClaim
from app.models.claim_request import ACTION_EXTEND, ACTION_RELEASE
from app.models.claim_request import STATUS_PENDING as REQUEST_PENDING
from app.models.claim_request import ClaimRequest
from app.models.company import Company
from app.schemas.claim import ClaimOut

AUTO_APPROVE_MAX_DAYS = 2


class ClaimError(Exception):
    pass


class CompanyAlreadyClaimed(ClaimError):
    def __init__(self, company_id: int) -> None:
        self.company_id = company_id
        super().__init__(f"company {company_id} is already claimed by another operator")


class ActiveClaimExists(ClaimError):
    def __init__(self, claim: CompanyClaim) -> None:
        self.claim = claim
        super().__init__(f"operator already has an active claim (id={claim.id})")


class OverdueClaimsBlock(ClaimError):
    def __init__(self, claims: list[CompanyClaim]) -> None:
        self.claims = claims
        super().__init__("operator has overdue deferred claims")


def is_overdue(claim: CompanyClaim, *, now: datetime | None = None) -> bool:
    if claim.status != STATUS_DEFERRED or claim.deadline_at is None:
        return False
    now = now or datetime.now(UTC)
    return claim.deadline_at < now


async def to_claim_out(session: AsyncSession, claim: CompanyClaim) -> ClaimOut:
    company = await session.get(Company, claim.company_id)
    return ClaimOut(
        id=claim.id,
        company_id=claim.company_id,
        company_name=company.name if company else "",
        operator_id=claim.operator_id,
        claimed_at=claim.claimed_at,
        status=claim.status,
        deadline_at=claim.deadline_at,
        deadline_days=claim.deadline_days,
        overdue=is_overdue(claim),
    )


async def get_active_claim(session: AsyncSession, operator_id: int) -> CompanyClaim | None:
    return (
        await session.execute(
            select(CompanyClaim).where(CompanyClaim.operator_id == operator_id, CompanyClaim.status == STATUS_ACTIVE)
        )
    ).scalar_one_or_none()


async def get_deferred_claims(session: AsyncSession, operator_id: int) -> list[CompanyClaim]:
    return list(
        (
            await session.execute(
                select(CompanyClaim).where(
                    CompanyClaim.operator_id == operator_id, CompanyClaim.status == STATUS_DEFERRED
                )
            )
        )
        .scalars()
        .all()
    )


async def get_overdue_claims(session: AsyncSession, operator_id: int) -> list[CompanyClaim]:
    deferred = await get_deferred_claims(session, operator_id)
    return [c for c in deferred if is_overdue(c)]


async def claim_company(session: AsyncSession, operator_id: int, company_id: int) -> CompanyClaim:
    """Raises OverdueClaimsBlock, ActiveClaimExists, or CompanyAlreadyClaimed
    when the claim can't proceed yet -- callers translate these into the
    appropriate HTTP response."""
    overdue = await get_overdue_claims(session, operator_id)
    if overdue:
        raise OverdueClaimsBlock(overdue)

    existing_active = await get_active_claim(session, operator_id)
    if existing_active is not None:
        if existing_active.company_id == company_id:
            return existing_active  # already their own active claim -- just re-open it
        raise ActiveClaimExists(existing_active)

    already_claimed = (
        await session.execute(
            select(CompanyClaim).where(
                CompanyClaim.company_id == company_id,
                CompanyClaim.status.in_([STATUS_ACTIVE, STATUS_DEFERRED]),
            )
        )
    ).scalar_one_or_none()
    if already_claimed is not None and already_claimed.operator_id != operator_id:
        raise CompanyAlreadyClaimed(company_id)

    claim = CompanyClaim(
        company_id=company_id,
        operator_id=operator_id,
        claimed_at=datetime.now(UTC),
        status=STATUS_ACTIVE,
    )
    session.add(claim)
    await session.flush()
    return claim


async def defer_claim(
    session: AsyncSession, claim: CompanyClaim, *, days: int, reason: str | None
) -> tuple[bool, ClaimRequest | None]:
    """Returns (auto_approved, claim_request). auto_approved=True means the
    claim is already deferred with its deadline set; otherwise a pending
    ClaimRequest was created and the claim is untouched until an admin acts."""
    if days <= AUTO_APPROVE_MAX_DAYS:
        claim.status = STATUS_DEFERRED
        claim.deadline_days = days
        claim.deadline_at = datetime.now(UTC) + timedelta(days=days)
        await session.flush()
        return True, None

    request = ClaimRequest(
        claim_id=claim.id,
        operator_id=claim.operator_id,
        action=ACTION_EXTEND,
        requested_days=days,
        reason=reason,
        status=REQUEST_PENDING,
    )
    session.add(request)
    await session.flush()
    return False, request


async def request_release(session: AsyncSession, claim: CompanyClaim, *, reason: str) -> ClaimRequest:
    request = ClaimRequest(
        claim_id=claim.id,
        operator_id=claim.operator_id,
        action=ACTION_RELEASE,
        reason=reason,
        status=REQUEST_PENDING,
    )
    session.add(request)
    await session.flush()
    return request


async def request_extend(session: AsyncSession, claim: CompanyClaim, *, days: int, reason: str) -> ClaimRequest:
    """Used when an already-overdue deferred claim needs more time -- same
    shape as defer_claim's admin-approval path, always pending regardless of
    day count (the auto-approve window is only for the initial move-on)."""
    request = ClaimRequest(
        claim_id=claim.id,
        operator_id=claim.operator_id,
        action=ACTION_EXTEND,
        requested_days=days,
        reason=reason,
        status=REQUEST_PENDING,
    )
    session.add(request)
    await session.flush()
    return request


async def complete_claims_for(session: AsyncSession, *, company_id: int, operator_id: int) -> None:
    """Called after a full review submission (both fields locked) so the
    claim stops counting toward the operator's active/deferred state."""
    claims = (
        (
            await session.execute(
                select(CompanyClaim).where(
                    CompanyClaim.company_id == company_id,
                    CompanyClaim.operator_id == operator_id,
                    CompanyClaim.status.in_([STATUS_ACTIVE, STATUS_DEFERRED]),
                )
            )
        )
        .scalars()
        .all()
    )
    for claim in claims:
        claim.status = STATUS_COMPLETED
    if claims:
        await session.flush()


async def resolve_extend(session: AsyncSession, claim: CompanyClaim, *, days: int) -> None:
    claim.status = STATUS_DEFERRED
    claim.deadline_days = days
    claim.deadline_at = datetime.now(UTC) + timedelta(days=days)
    await session.flush()


async def resolve_release(session: AsyncSession, claim: CompanyClaim) -> None:
    claim.status = STATUS_RELEASED
    await session.flush()
