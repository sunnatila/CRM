from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# The five lead statuses. Uzbek labels live in the frontend -- these identifiers
# never reach a screen.
STATUS_NEW = "new"  # Yangi -- nobody has touched it; represented by the ABSENCE of a row
STATUS_IN_PROGRESS = "in_progress"  # Jarayonda -- exclusively held by one operator
STATUS_WAITING = "waiting"  # Kutilmoqda -- started, unfinished, held by nobody
STATUS_APPROVED = "approved"  # Tasdiqlangan
STATUS_REJECTED = "rejected"  # Rad etilgan

LEAD_STATUSES = (STATUS_NEW, STATUS_IN_PROGRESS, STATUS_WAITING, STATUS_APPROVED, STATUS_REJECTED)

# Statuses that hold an assignee. Every other status has assigned_to_id = NULL --
# this is an invariant the service layer maintains, not just a convention.
ASSIGNED_STATUSES = (STATUS_IN_PROGRESS,)

# Event types written to lead_events. actor_id IS NULL means the system did it.
EVENT_STATUS_CHANGE = "status_change"
EVENT_HANDOVER = "handover"  # the mandatory comment when leaving an in-progress lead
EVENT_COMMENT = "comment"  # free-form, no status change
EVENT_FINISH = "finish"
EVENT_REOPEN = "reopen"
EVENT_AUTO_RELEASE = "auto_release"
EVENT_ADMIN_RELEASE = "admin_release"
EVENT_ADMIN_ASSIGN = "admin_assign"
EVENT_MIGRATION = "migration"


class LeadState(Base):
    """One row per company, created lazily on first touch.

    A missing row means STATUS_NEW -- the queue reads it with an outer join and
    COALESCE rather than backfilling every company, so the scrape pipeline can
    keep inserting into `companies` without ever writing to the review domain
    (ARCHITECTURE-SPINE AD-2).
    """

    __tablename__ = "lead_states"
    __table_args__ = (
        Index("ix_lead_states_status_activity", "status", "last_activity_at"),
        Index("ix_lead_states_assignee_status", "assigned_to_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default=STATUS_NEW)
    # Only ever set while status == in_progress; cleared on every exit from it.
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Drives the 4-hour auto-release. Bumped by claims, draft saves and comments --
    # anything that proves the operator is still on it.
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Who touched it last, in any status -- powers "Malika, 2 soat oldin" in the
    # waiting list without a join back through lead_events.
    last_actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"LeadState(company_id={self.company_id}, status={self.status!r}, assigned_to_id={self.assigned_to_id})"


class LeadEvent(Base):
    """Append-only timeline. This is the control mechanism that replaced the old
    lock/permission gate: anyone may change anything, nothing goes unrecorded.

    No service function updates or deletes a row here, deliberately.
    """

    __tablename__ = "lead_events"
    __table_args__ = (Index("ix_lead_events_company_created", "company_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # NULL = system
    type: Mapped[str] = mapped_column(String(24))
    from_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"LeadEvent(company_id={self.company_id}, type={self.type!r}, to_status={self.to_status!r})"
