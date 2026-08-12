from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

FIELD_WEBSITE = "website"
FIELD_LMS = "lms"
REVIEW_FIELDS = (FIELD_WEBSITE, FIELD_LMS)


class CompanyReview(Base):
    """AD-8: one row per (company_id, field). A locked row is only reopened via an
    approved PermissionRequest -- never a direct unlock."""

    __tablename__ = "company_reviews"
    __table_args__ = (UniqueConstraint("company_id", "field", name="uq_review_company_field"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    field: Mapped[str] = mapped_column(String(16))
    available: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    filled_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"CompanyReview(company_id={self.company_id}, field={self.field!r}, locked={self.locked})"
