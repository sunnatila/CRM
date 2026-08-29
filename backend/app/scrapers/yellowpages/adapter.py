"""yellowpages.uz adapter.

Re-measured 2026-08-29: **this source needs no browser at all.**

The original July note ("a Nuxt 3 app where listings and detail data are populated
client-side, so drive Playwright") was true when written and has not been true for
a while. Both the rubric listing and the company detail page are server-rendered:
the listing's company links and the detail page's schema.org JSON-LD + #contacts
card are all present in the raw HTML.

Pagination is a plain query parameter, `?pagenumber=N`. That was missed twice:
`?page=N` is *accepted and silently ignored* (it returns page 1), which made
pagination look client-only, and the Ant Design "next" control is `display:none`
in the DOM, so a headless click on it times out. Both dead ends -- the real
mechanism is a URL the server honours.

Crawl shape: /en/list -> rubric slugs -> /en/rubric/{slug}?pagenumber=N -> company
slugs -> /en/company/{slug}.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import AsyncIterator

import httpx
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.scrapers.base import CompanyIn, RawRecord, SourceAdapter
from app.scrapers.jsonld import extract_local_business
from app.scrapers.resilience import (
    BROWSER_HEADERS,
    FailureBudget,
    ProxyRotator,
    RateLimiter,
    guarded,
    request_with_retry,
)

logger = logging.getLogger(__name__)

# 15 companies per listing page; the cap is a runaway guard, not an expected limit.
_MAX_PAGES_PER_RUBRIC = 200


class YellowPagesAdapter(SourceAdapter):
    source = "yellowpages"

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.yellowpages_base_url.rstrip("/")
        self.limiter = RateLimiter(settings.scraper_request_delay_seconds)
        self.budget = FailureBudget()
        self.proxies = ProxyRotator()
        self.concurrency = max(1, settings.scraper_concurrency)

    async def _fetch_batch(
        self, slugs: list[str], rubric_label: str, client: httpx.AsyncClient
    ) -> list[RawRecord]:
        """Fetch several company pages at once over plain HTTP.

        Each fetch still passes through the shared RateLimiter, so this raises
        utilisation (overlapping the wait for each response) without raising the
        request rate the site sees.
        """
        if not slugs:
            return []

        results = await asyncio.gather(
            *(
                guarded(
                    self.budget,
                    f"company {slug}",
                    lambda s=slug: self._fetch_company(client, s, rubric_label),
                )
                for slug in slugs
            ),
            return_exceptions=True,
        )

        records: list[RawRecord] = []
        fatal: BaseException | None = None
        for slug, res in zip(slugs, results, strict=True):
            if isinstance(res, BaseException):
                # gather() collected it rather than unwinding; ScrapeAborted /
                # SourceBlocked / cancellation still have to end the run, so
                # re-raise after the whole batch is accounted for.
                fatal = fatal or res
                continue
            if res is not None:
                records.append(RawRecord(source_id=slug, payload=res))
        if fatal is not None:
            raise fatal
        return records

    async def fetch_raw(self, skip_ids: set[str] | None = None) -> AsyncIterator[RawRecord]:
        skip_ids = skip_ids or set()
        rubrics = await self._discover_rubrics()
        seen_company_slugs: set[str] = set()

        async with httpx.AsyncClient(
            headers=BROWSER_HEADERS,
            timeout=30,
            follow_redirects=True,
            proxy=self.proxies.next_proxy(),
            limits=httpx.Limits(max_connections=self.concurrency * 2),
        ) as client:
            for rubric_slug, rubric_label in rubrics.items():
                # AD-16: a rubric already walked end to end is not re-enumerated.
                if rubric_slug in self.done_rubrics:
                    continue
                seen_here = 0
                batch: list[str] = []

                async for company_slug in self._iter_rubric_company_slugs(client, rubric_slug):
                    seen_here += 1
                    if company_slug in seen_company_slugs or company_slug in skip_ids:
                        continue
                    seen_company_slugs.add(company_slug)
                    batch.append(company_slug)
                    if len(batch) < self.concurrency:
                        continue
                    for rec in await self._fetch_batch(batch, rubric_label, client):
                        yield rec
                    batch = []

                for rec in await self._fetch_batch(batch, rubric_label, client):
                    yield rec

                # Reached only if the rubric was enumerated without the consumer
                # breaking out (e.g. hitting `limit`), so a partial walk is never
                # recorded as complete.
                if self.on_rubric_complete is not None:
                    await self.on_rubric_complete(rubric_slug, seen_here)

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

    async def _discover_rubrics(self) -> dict[str, str]:
        """Returns {slug: display_label}, e.g. {"accountants-training": "Accountants - Training"}."""
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers=BROWSER_HEADERS,
            timeout=30,
            follow_redirects=True,
            proxy=self.proxies.next_proxy(),
        ) as client:
            # Not guarded: no rubric catalog means no crawl, so a failure here
            # (after retries) should surface as a failed run.
            resp = await request_with_retry(client, "/en/list", limiter=self.limiter)
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        rubrics: dict[str, str] = {}
        for a in soup.select('a[href^="/en/rubric/"]'):
            slug = a["href"].removeprefix("/en/rubric/").strip("/")
            label = a.get_text(strip=True)
            if slug and label:
                rubrics[slug] = label
        return rubrics

    async def _iter_rubric_company_slugs(
        self, client: httpx.AsyncClient, rubric_slug: str
    ) -> AsyncIterator[str]:
        """Walk one rubric's listing pages via `?pagenumber=N`.

        Termination is "this page introduced nothing new" rather than a parsed
        page count: past the last page the site still returns 200 with a valid
        shell, so a status check alone would loop to the runaway cap.
        """
        seen: set[str] = set()
        for page_no in range(1, _MAX_PAGES_PER_RUBRIC + 1):
            url = f"{self.base_url}/en/rubric/{rubric_slug}"
            if page_no > 1:
                url = f"{url}?pagenumber={page_no}"

            resp = await guarded(
                self.budget,
                f"rubric {rubric_slug} page {page_no}",
                lambda u=url: request_with_retry(client, u, limiter=self.limiter),
            )
            if resp is None or resp.status_code != 200:
                return

            new_slugs = self._extract_company_slugs(resp.text) - seen
            if not new_slugs:
                return
            for slug in new_slugs:
                seen.add(slug)
                yield slug

    @staticmethod
    def _extract_company_slugs(html: str) -> set[str]:
        slugs = set()
        for href in re.findall(r'href="(/en/company/[^"#]+)"', html):
            slug = href.removeprefix("/en/company/").strip("/")
            if slug and slug != "add":
                slugs.add(slug)
        return slugs

    async def _fetch_company(self, client: httpx.AsyncClient, company_slug: str, rubric_label: str) -> dict | None:
        """Plain HTTP -- no browser.

        Re-measured 2026-08-20: the company detail page is server-rendered. Both
        the JSON-LD block and the #contacts card are present in the raw HTML, so
        the Playwright round-trip this used to do (launch a tab, render ads and
        analytics, wait 1.5s, read the DOM) bought nothing. Dropping it removes
        the overwhelming majority of browser work in this crawl -- detail pages
        outnumber listing pages by a large factor -- which is what made the
        browser OOM under any concurrency. The listing walk no longer needs one
        either -- see the module docstring.
        """
        url = f"{self.base_url}/en/company/{company_slug}"
        resp = await request_with_retry(client, url, limiter=self.limiter)
        if resp.status_code != 200:
            return None
        html = resp.text

        business = extract_local_business(html)
        if business is None:
            return None

        address = business.get("address", {})
        street_address = address.get("streetAddress") if isinstance(address, dict) else None

        # The JSON-LD "email"/"telephone" fields are frequently blank even when the page
        # itself shows them -- the #contacts card (rendered client-side) is the more
        # complete source, and it's also the only place the company's real "Website:"
        # is shown at all (JSON-LD "url" there is just the yellowpages profile page).
        soup = BeautifulSoup(html, "lxml")
        contacts_email = _contacts_field(soup, "E-mail:")
        contacts_website = _contacts_field(soup, "Website:")

        website = _normalize_url(contacts_website[0]) if contacts_website else None
        email = ", ".join(contacts_email) if contacts_email else (business.get("email") or None)

        return {
            "name": business.get("name"),
            "category": rubric_label,
            "address": street_address,
            "phone": business.get("telephone") or None,  # yellowpages masks phone numbers behind a "Call"
            "email": email,  # button that a plain page load/click never reveals -- not scrapable as-is.
            "website": website,
            "logo_url": None,  # no company logo/photo element found on the detail page in testing
            "working_hours": None,
            "source_url": url,
            "raw_extra": {
                "rating": business.get("aggregateRating"),
                "geo": business.get("geo"),
            },
        }


def _contacts_field(soup: BeautifulSoup, label: str) -> list[str]:
    """Read a "<label> <a>value</a>[, <a>value</a>...]" row from the #contacts card."""
    for h3 in soup.select("#contacts h3"):
        if h3.get_text(strip=True).startswith(label):
            return [a.get_text(strip=True) for a in h3.select("a") if a.get_text(strip=True)]
    return []


def _normalize_url(value: str) -> str:
    return value if re.match(r"^https?://", value) else f"https://{value}"
