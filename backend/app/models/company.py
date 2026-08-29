from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_company_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    # Observed 2026-08-27: a yellowpages slug can be raw Cyrillic, which
    # percent-encoded in the URL path (each character -> 6 bytes, "%D0%B8...")
    # comfortably exceeds 128 chars -- killed a run with the same class of
    # truncation error as the fields below, just on the identifier column
    # instead of a content one. Same fix, same reasoning.
    source_id: Mapped[str] = mapped_column(Text, index=True)
    # Every field below is scraped free text with no reliable upper bound: a
    # company can sit in 20 categories, list 8 phone numbers, or carry a very
    # long name. A VARCHAR(n) guess here doesn't validate anything -- it just
    # aborts the transaction mid-crawl when real data exceeds it (observed:
    # a 1400-char category list killed a whole goldenpages run). Postgres
    # stores TEXT and VARCHAR(n) identically, so the cap bought nothing.
    name: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    website: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    working_hours: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"Company(id={self.id}, source={self.source!r}, name={self.name!r})"
