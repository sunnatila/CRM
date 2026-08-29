from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RubricProgress(Base):
    """One row per (source, rubric) that has been walked end to end (AD-16).

    Without this, resuming an interrupted crawl is O(whole catalog): the adapter
    re-walks every rubric from the top, re-loading hundreds of listing pages just
    to re-discover companies `skip_ids` then throws away. On yellowpages that is
    718 Playwright page loads -- close to an hour of work producing zero new rows.

    Recording a rubric as done makes resume O(remaining work) instead. It is
    deliberately separate from `companies`: "this rubric was fully enumerated" is
    crawl bookkeeping, not a property of any company, and a rubric can legitimately
    complete having yielded nothing new.
    """

    __tablename__ = "rubric_progress"
    __table_args__ = (UniqueConstraint("source", "rubric_key", name="uq_rubric_progress"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    rubric_key: Mapped[str] = mapped_column(String(512), index=True)
    companies_seen: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"RubricProgress(source={self.source!r}, rubric_key={self.rubric_key!r})"
