from datetime import datetime

from pydantic import BaseModel


class ClaimOut(BaseModel):
    id: int
    company_id: int
    company_name: str
    operator_id: int
    claimed_at: datetime
    status: str
    deadline_at: datetime | None
    deadline_days: int | None
    overdue: bool


class MyClaimsOut(BaseModel):
    active: ClaimOut | None
    deferred: list[ClaimOut]


class DeferClaimIn(BaseModel):
    days: int
    reason: str | None = None


class ReleaseClaimIn(BaseModel):
    reason: str


class DeferResultOut(BaseModel):
    auto_approved: bool
    claim: ClaimOut | None = None
    claim_request_id: int | None = None


class ResolveClaimRequestIn(BaseModel):
    note: str | None = None


class ClaimRequestOut(BaseModel):
    id: int
    claim_id: int
    company_id: int
    company_name: str
    operator_id: int
    operator_name: str
    action: str
    requested_days: int | None
    reason: str | None
    status: str
    created_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None
