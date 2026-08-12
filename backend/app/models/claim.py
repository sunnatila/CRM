from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

STATUS_ACTIVE = "active"  # the one operator is meant to be working on right now
STATUS_DEFERRED = "deferred"  # set aside with a committed deadline, operator moved to a new claim
STATUS_COMPLETED = "completed"  # both review fields got submitted
STATUS_RELEASED = "released"  # admin approved a release request -- company is unassigned again

CLAIM_STATUSES = (STATUS_ACTIVE, STATUS_DEFERRED, STATUS_COMPLETED, STATUS_RELEASED)


class CompanyClaim(Base):
    """One operator working one company at a time (AD-11). A company with an
    active/deferred claim is invisible to everyone else's queue."""

    __tablename__ = "company_claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    operator_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16), default=STATUS_ACTIVE)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"CompanyClaim(id={self.id}, company_id={self.company_id}, status={self.status!r})"
