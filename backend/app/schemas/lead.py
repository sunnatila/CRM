from datetime import datetime

from pydantic import BaseModel, Field

from app.models.lead import STATUS_APPROVED, STATUS_REJECTED


class LeadFieldOut(BaseModel):
    field: str  # "website" | "lms"
    available: bool | None  # None = belgilanmagan (a real third state in v2)
    comment: str | None
    filled_by: str | None
    filled_at: datetime | None


class LeadEventOut(BaseModel):
    id: int
    type: str
    actor: str | None  # None renders as "Tizim"
    from_status: str | None
    to_status: str | None
    note: str | None
    created_at: datetime


class LeadListItemOut(BaseModel):
    id: int
    name: str
    category: str | None
    address: str | None
    phone: str | None
    source: str
    status: str
    assignee_id: int | None
    assignee_name: str | None
    website_available: bool | None
    lms_available: bool | None
    # The handover comment, surfaced in the row itself so an operator can judge a
    # waiting lead without opening it (FR-12).
    last_note: str | None
    last_note_by: str | None
    last_note_at: datetime | None


class CategoryOut(BaseModel):
    """A category plus how many companies carry it.

    The count is the whole point: 3.6k categories sorted alphabetically are
    unbrowsable -- the operator cannot tell "Завод в Узбекистане" (1008 leads)
    from a tag that matches three companies. Ordering by count turns the list
    into something you can actually explore without knowing a name in advance.
    """

    name: str
    count: int


class LeadListOut(BaseModel):
    items: list[LeadListItemOut]
    total: int
    # Every tab's badge in one response -- the v1 queue paid for a second
    # round trip just to render these.
    counts: dict[str, int]


class LeadDetailOut(BaseModel):
    id: int
    name: str
    category: str | None
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    source: str
    source_url: str | None
    status: str
    assignee_id: int | None
    assignee_name: str | None
    assigned_at: datetime | None
    last_activity_at: datetime | None
    fields: list[LeadFieldOut]
    events: list[LeadEventOut]
    # The server owns the state machine; the client renders whatever is in here
    # rather than re-deriving the rules (FR-2).
    available_actions: list[str]


class LeadAttentionItemOut(BaseModel):
    id: int
    name: str
    status: str
    reason: str  # "stale" | "handoffs"
    waiting_days: int | None
    handoff_count: int | None
    last_note: str | None
    # Who was holding it when it went quiet. The distinction is the actionable
    # half: "nobody has picked this up" and "an operator took it and walked
    # away" need different responses from the admin.
    last_holder: str | None = None


class NoteIn(BaseModel):
    note: str | None = None


class SwitchIn(BaseModel):
    from_company_id: int
    note: str | None = None


class FinishIn(BaseModel):
    result: str = Field(pattern=f"^({STATUS_APPROVED}|{STATUS_REJECTED})$")
    note: str | None = None


class AssignIn(BaseModel):
    operator_id: int
    note: str | None = None


class DraftFieldIn(BaseModel):
    available: bool | None = None
    comment: str | None = None


class DraftIn(BaseModel):
    # Either may be omitted: v2 saves whatever the operator has decided so far.
    website: DraftFieldIn | None = None
    lms: DraftFieldIn | None = None
