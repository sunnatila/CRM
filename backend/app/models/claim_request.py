from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

ACTION_EXTEND = "extend"
ACTION_RELEASE = "release"

STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_DENIED = "denied"


class ClaimRequest(Base):
    """The only path that moves a CompanyClaim past AD-11's >2-day auto-approve
    ceiling (extend) or gives it up entirely (release) -- mirrors PermissionRequest's
    shape for the review-lock domain (AD-8), one row per ask."""

    __tablename__ = "claim_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("company_claims.id"), index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(16))
    requested_days: Mapped[int | None] = mapped_column(Integer, nullable=True)  # only for "extend"
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=STATUS_PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"ClaimRequest(id={self.id}, claim_id={self.claim_id}, action={self.action!r}, status={self.status!r})"
