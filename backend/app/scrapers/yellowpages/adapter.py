"""yellowpages.uz adapter.

Confirmed (2026-07-26, by rendering real pages): a Nuxt 3 app where rubric listings
and company detail data are populated client-side after load -- a plain HTTP GET does
not see them, so this adapter drives a real (headless) browser via Playwright. Like
goldenpages, company detail pages carry a schema.org LocalBusiness JSON-LD block once
rendered, so normalization reuses the same jsonld helper.

The rubric *catalog* itself (chapter/rubric slugs) IS server-rendered on /en/list, so
that discovery step stays a plain httpx call -- no browser needed for it.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.core.config import get_settings
from app.scrapers.base import CompanyIn, RawRecord, SourceAdapter
from app.scrapers.jsonld import extract_local_business

_REQUEST_DELAY_SECONDS = 0.3
_PAGE_TIMEOUT_MS = 30_000
_MAX_PAGES_PER_RUBRIC = 50
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ParsingProjectBot/1.0)"}


class YellowPagesAdapter(SourceAdapter):
    source = "yellowpages"

    def __init__(self) -> None:
        self.base_url = get_settings().yellowpages_base_url.rstrip("/")

    async def fetch_raw(self, skip_ids: set[str] | None = None) -> AsyncIterator[RawRecord]:
        skip_ids = skip_ids or set()
        rubrics = await self._discover_rubrics()
        seen_company_slugs: set[str] = set()

        async with async_playwright() as pw:
            # --disable-dev-shm-usage: Docker's default /dev/shm is 64MB, too
            # small for Chromium's shared memory needs -- without this it
            # silently stalls page loads (observed as Page.goto timeouts),
            # especially on low-memory hosts. Makes Chromium use /tmp instead.
            browser = await pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                context = await browser.new_context(user_agent=_HEADERS["User-Agent"])

                for rubric_slug, rubric_label in rubrics.items():
                    async for company_slug in self._iter_rubric_company_slugs(context, rubric_slug):
                        if company_slug in seen_company_slugs or company_slug in skip_ids:
                            continue
                        seen_company_slugs.add(company_slug)

                        payload = await self._fetch_company(context, company_slug, rubric_label)
                        if payload is None:
                            continue
                        yield RawRecord(source_id=company_slug, payload=payload)
            finally:
                await browser.close()

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
        async with httpx.AsyncClient(base_url=self.base_url, headers=_HEADERS, timeout=30) as client:
            resp = await client.get("/en/list")
            resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        rubrics: dict[str, str] = {}
        for a in soup.select('a[href^="/en/rubric/"]'):
            slug = a["href"].removeprefix("/en/rubric/").strip("/")
            label = a.get_text(strip=True)
            if slug and label:
                rubrics[slug] = label
        return rubrics

    async def _iter_rubric_company_slugs(self, context, rubric_slug: str) -> AsyncIterator[str]:
        page = await context.new_page()
        try:
            await page.goto(
                f"{self.base_url}/en/rubric/{rubric_slug}",
                wait_until="domcontentloaded",
                timeout=_PAGE_TIMEOUT_MS,
            )
            await page.wait_for_timeout(2000)

            seen: set[str] = set()
            for _ in range(_MAX_PAGES_PER_RUBRIC):
                slugs = await self._extract_company_slugs(page)
                new_slugs = slugs - seen
                if not new_slugs and seen:
                    return
                for slug in new_slugs:
                    seen.add(slug)
                    yield slug

                next_control = page.get_by_text(re.compile(r"^Next"), exact=False).last
                try:
                    if await next_control.count() == 0:
                        return
                    await next_control.click(timeout=3000)
                    await page.wait_for_timeout(1500)
                except Exception:
                    return
        finally:
            await page.close()

    async def _extract_company_slugs(self, page) -> set[str]:
        hrefs = await page.locator('a[href^="/en/company/"]').evaluate_all(
            "els => els.map(e => e.getAttribute('href'))"
        )
        slugs = set()
        for href in hrefs:
            slug = href.split("#")[0].removeprefix("/en/company/").strip("/")
            if slug and slug != "add":
                slugs.add(slug)
        return slugs

    async def _fetch_company(self, context, company_slug: str, rubric_label: str) -> dict | None:
        await asyncio.sleep(_REQUEST_DELAY_SECONDS)
        page = await context.new_page()
        try:
            url = f"{self.base_url}/en/company/{company_slug}"
            await page.goto(url, wait_until="domcontentloaded", timeout=_PAGE_TIMEOUT_MS)
            await page.wait_for_timeout(1500)
            html = await page.content()
        finally:
            await page.close()

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
