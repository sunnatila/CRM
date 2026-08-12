from datetime import datetime

from pydantic import BaseModel


class ReviewFieldIn(BaseModel):
    available: bool
    comment: str


class ReviewSubmitIn(BaseModel):
    # Both optional: a first-time fill submits both; a refill after a per-field
    # reopen (AD-8) submits only the field that was unlocked -- the other, still
    # locked, is left untouched.
    website: ReviewFieldIn | None = None
    lms: ReviewFieldIn | None = None


class ReviewFieldOut(BaseModel):
    field: str
    available: bool | None
    comment: str | None
    filled_by: str | None  # full_name, for display
    filled_at: datetime | None
    locked: bool
    pending_request: bool  # true if a permission request is awaiting admin decision


class CompanyQueueItemOut(BaseModel):
    id: int
    name: str
    category: str | None
    address: str | None
    phone: str | None
    source: str
    website_status: str  # "pending" | "confirmed" | "absent"
    lms_status: str


class CompanyReviewDetailOut(BaseModel):
    id: int
    name: str
    category: str | None
    address: str | None
    phone: str | None
    email: str | None
    source: str
    fields: list[ReviewFieldOut]


class PermissionRequestIn(BaseModel):
    reason: str | None = None


class ResolvePermissionRequestIn(BaseModel):
    note: str | None = None


class PermissionRequestOut(BaseModel):
    id: int
    review_id: int
    company_id: int
    company_name: str
    field: str
    requested_by: str
    reason: str | None
    status: str
    created_at: datetime
    resolved_at: datetime | None
    resolution_note: str | None


class NotificationOut(BaseModel):
    id: int
    message: str
    link: str | None
    read: bool
    created_at: datetime


class OperatorStatsOut(BaseModel):
    id: int
    username: str
    full_name: str
    avatar_url: str | None
    today_count: int
    week_count: int
    total_count: int


class OverviewStatsOut(BaseModel):
    today_filled: int
    week_filled: int
    pending_requests: int
    active_operators: int
