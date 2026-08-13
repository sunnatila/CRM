from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    source_id: str
    name: str
    category: str | None
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    logo_url: str | None
    working_hours: str | None
    source_url: str | None
    first_seen_at: datetime
    last_seen_at: datetime


class ScrapeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    records_found: int
    records_upserted: int
    records_failed: int
    error_message: str | None
