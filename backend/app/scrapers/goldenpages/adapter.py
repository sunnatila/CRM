"""goldenpages.uz adapter.

Confirmed (2026-07-26, by fetching real pages): classic server-rendered HTML, no JS
needed. Company detail pages embed a schema.org LocalBusiness JSON-LD block with
name/address/telephone/openingHoursSpecification/geo -- that's the primary source of
truth here, not loose HTML scraping. Category ("Виды деятельности") is a plain list of
<a href="/rubrics/?Id=..."> links on the same detail page.

Crawl shape: homepage -> rubric ids (+ names) -> paginated rubric listing -> company
ids -> company detail page.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.scrapers.base import CompanyIn, RawRecord, SourceAdapter
from app.scrapers.jsonld import extract_local_business
from app.scrapers.resilience import (
    FailureBudget,
    ProxyRotator,
    RateLimiter,
    guarded,
    request_with_retry,
)

_MAX_PAGES_PER_RUBRIC = 200
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ParsingProjectBot/1.0)"}


class GoldenPagesAdapter(SourceAdapter):
    source = "goldenpages"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.goldenpages_base_url.rstrip("/")
        self.limiter = RateLimiter(settings.scraper_request_delay_seconds)
        self.budget = FailureBudget()
        self.proxies = ProxyRotator()

    async def fetch_raw(self, skip_ids: set[str] | None = None) -> AsyncIterator[RawRecord]:
        skip_ids = skip_ids or set()
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=_HEADERS,
            timeout=30,
            follow_redirects=True,
            proxy=self.proxies.next_proxy(),
        ) as client:
            rubrics = await self._discover_rubrics(client)
            seen_company_ids: set[str] = set()

            for rubric_id in rubrics:
                async for company_id in self._iter_rubric_company_ids(client, rubric_id):
                    if company_id in seen_company_ids or company_id in skip_ids:
                        continue
                    seen_company_ids.add(company_id)

                    # One unreachable company page must not end the crawl -- it's
                    # skipped and counted, and only an unbroken streak aborts.
                    payload = await guarded(
                        self.budget,
                        f"company {company_id}",
                        lambda cid=company_id: self._fetch_company(client, cid),
                    )
                    if payload is None:
                        continue
                    yield RawRecord(source_id=company_id, payload=payload)

    def normalize(self, raw: RawRecord) -> CompanyIn:
        p = raw.payload
        return CompanyIn(
            source=self.source,
            source_id=raw.source_id,
            name=p["name"],
            category=p.get("category"),
            address=p.get("address"),
            phone=p.get("phone"),
            email=p.get("email"),
            website=p.get("website"),
            logo_url=p.get("logo_url"),
            working_hours=p.get("working_hours"),
            source_url=p.get("source_url"),
            raw_extra=p.get("raw_extra"),
        )

    async def _discover_rubrics(self, client: httpx.AsyncClient) -> list[str]:
        # Not guarded: without the rubric list there is no crawl at all, so a
        # failure here (after retries) should surface as a failed run.
        resp = await request_with_retry(client, "/", limiter=self.limiter)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        ids: dict[str, None] = {}
        for a in soup.select('a[href^="/rubrics/?Id="]'):
            text = a.get_text(strip=True)
            if not text:
                continue
            match = re.search(r"Id=(\d+)", a["href"])
            if match:
                ids[match.group(1)] = None
        return list(ids.keys())

    async def _iter_rubric_company_ids(self, client: httpx.AsyncClient, rubric_id: str) -> AsyncIterator[str]:
        for page in range(1, _MAX_PAGES_PER_RUBRIC + 1):
            url = f"/rubrics/?Id={rubric_id}&Page={page}" if page > 1 else f"/rubrics/?Id={rubric_id}"
            # A dead listing page ends this rubric but leaves the rest of the
            # crawl running -- there are hundreds of other rubrics to walk.
            resp = await guarded(
                self.budget,
                f"rubric {rubric_id} page {page}",
                lambda u=url: request_with_retry(client, u, limiter=self.limiter),
            )
            if resp is None or resp.status_code != 200:
                return
            soup = BeautifulSoup(resp.text, "lxml")

            company_ids = set()
            for a in soup.select('a[href^="/company/?Id="]'):
                match = re.search(r"Id=(\d+)", a["href"])
                if match:
                    company_ids.add(match.group(1))
            for company_id in company_ids:
                yield company_id

            has_next = soup.select_one("li.gp_next a") is not None
            if not has_next or not company_ids:
                return

    async def _fetch_company(self, client: httpx.AsyncClient, company_id: str) -> dict | None:
        url = f"/company/?Id={company_id}"
        resp = await request_with_retry(client, url, limiter=self.limiter)
        if resp.status_code != 200:
            return None

        business = extract_local_business(resp.text)
        if business is None:
            return None

        soup = BeautifulSoup(resp.text, "lxml")
        category = "; ".join(
            a.get_text(strip=True) for a in soup.select("ul.gp_Gy6z li a") if a.get_text(strip=True)
        ) or None

        logo_img = soup.select_one(".gp_logo_com img")
        logo_src = logo_img.get("src") if logo_img else None
        logo_url = (
            f"{self.base_url}{logo_src}"
            if logo_src and "no_logo" not in logo_src
            else None
        )

        address = business.get("address", {})
        street_address = address.get("streetAddress") if isinstance(address, dict) else None

        working_hours = _format_opening_hours(business.get("openingHoursSpecification"))

        return {
            "name": business.get("name"),
            "category": category,
            "address": street_address,
            "phone": business.get("telephone") or None,
            "email": business.get("email") or None,
            "website": None,  # JSON-LD "url"/"sameAs" here points back at goldenpages itself, not the company
            "logo_url": logo_url,
            "working_hours": working_hours,
            "source_url": f"{self.base_url}{url}",
            "raw_extra": {
                "rating": business.get("aggregateRating"),
                "geo": business.get("geo"),
            },
        }


def _format_opening_hours(spec: list | None) -> str | None:
    if not spec:
        return None
    parts = []
    for entry in spec:
        if not isinstance(entry, dict):
            continue
        day = str(entry.get("dayOfWeek", "")).rsplit("/", 1)[-1]
        opens = entry.get("opens")
        closes = entry.get("closes")
        if day and opens and closes:
            parts.append(f"{day}: {opens}-{closes}")
    return "; ".join(parts) or None
