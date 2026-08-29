from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from pydantic import BaseModel, ConfigDict


class RawRecord(BaseModel):
    """Unparsed-ish data pulled from a source, before normalization into CompanyIn."""

    model_config = ConfigDict(extra="allow")

    source_id: str
    payload: dict[str, Any]


class CompanyIn(BaseModel):
    """Shape every adapter must normalize into. AD-2 / AD-3 target."""

    source: str
    source_id: str
    name: str
    category: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None
    working_hours: str | None = None
    source_url: str | None = None
    raw_extra: dict[str, Any] | None = None


class SourceAdapter(ABC):
    """AD-4: the only surface api/ and admin/ may rely on -- never a concrete adapter's internals.

    Fetch mechanism (plain HTTP vs headless browser) is each adapter's own business.
    """

    source: str

    # AD-16 rubric-level resume. Set by the pipeline before `fetch_raw`, so that
    # `fetch_raw`'s signature (and every caller of it) stays unchanged:
    #   done_rubrics      -- rubric keys already fully walked; adapters skip these
    #   on_rubric_complete -- awaited with (rubric_key, companies_seen) once a
    #                         rubric has been enumerated end to end
    # Both default to "no resume info", so an adapter used standalone still works.
    done_rubrics: set[str] = frozenset()  # type: ignore[assignment]
    on_rubric_complete = None

    @abstractmethod
    def fetch_raw(self, skip_ids: set[str] | None = None) -> AsyncIterator[RawRecord]:
        """Yield raw records from the source. Records whose source_id is in skip_ids
        (already in our DB for this source) are not even fetched -- not just deduped."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw: RawRecord) -> CompanyIn:
        """Map one raw record into the shared Company shape."""
        raise NotImplementedError
