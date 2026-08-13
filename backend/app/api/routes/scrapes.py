import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.models.scrape_run import ScrapeRun
from app.schemas.company import ScrapeRunOut
from app.scrapers.pipeline import ADAPTERS, ScrapeAlreadyRunning, start_scrape, stop_scrape
from app.scrapers.resilience import BROWSER_HEADERS, ProxyRotator

router = APIRouter(prefix="/scrapes", tags=["scrapes"])


@router.get("/diagnose/{source}")
async def diagnose_source(source: str) -> dict:
    """Is this source reachable from *this* server right now, and what is our exit IP?

    Exists because "the scrape failed" has two very different causes that look
    identical from the outside: our code broke, or the source blocked this host.
    One request answers that without reading logs or re-running a whole crawl.
    """
    if source not in ADAPTERS:
        raise HTTPException(status_code=404, detail=f"unknown source, expected one of {sorted(ADAPTERS)}")

    settings = get_settings()
    base_url = getattr(settings, f"{source}_base_url").rstrip("/")
    proxy = ProxyRotator().next_proxy()

    result: dict = {"source": source, "url": base_url, "proxy": proxy or "(direct)"}

    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True, proxy=proxy) as client:
            resp = await client.get(base_url, headers=BROWSER_HEADERS)
        result["status_code"] = resp.status_code
        result["reachable"] = resp.status_code == 200
        if resp.status_code == 403:
            result["diagnosis"] = (
                "BLOCKED -- the source refused this server's IP. Not a code bug: wait for "
                "the ban to lapse, and/or set SCRAPER_PROXIES to route via another IP."
            )
        elif resp.status_code == 429:
            result["diagnosis"] = (
                "RATE LIMITED -- slow down: raise SCRAPER_REQUEST_DELAY_SECONDS and "
                "avoid triggering repeated runs back to back."
            )
        elif resp.status_code == 200:
            result["diagnosis"] = "OK -- source is reachable from this server, scraping should work."
        else:
            result["diagnosis"] = f"Unexpected status {resp.status_code}."
    except Exception as exc:  # noqa: BLE001 -- a diagnostic reports failures, doesn't raise them
        result["reachable"] = False
        result["diagnosis"] = f"Could not connect: {type(exc).__name__}: {exc}"

    # Our public exit IP, so a block can be correlated with what the source sees.
    try:
        async with httpx.AsyncClient(timeout=10, proxy=proxy) as client:
            result["exit_ip"] = (await client.get("https://api.ipify.org")).text.strip()
    except Exception:  # noqa: BLE001 -- best-effort extra context
        result["exit_ip"] = "(unknown)"

    return result


@router.get("", response_model=list[ScrapeRunOut])
async def list_scrape_runs(
    source: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[ScrapeRun]:
    stmt = select(ScrapeRun).order_by(ScrapeRun.id.desc()).limit(limit)
    if source:
        stmt = stmt.where(ScrapeRun.source == source)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{run_id}", response_model=ScrapeRunOut)
async def get_scrape_run(run_id: int, session: AsyncSession = Depends(get_session)) -> ScrapeRun:
    run = await session.get(ScrapeRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="scrape run not found")
    return run


@router.post("/{source}", response_model=ScrapeRunOut)
async def trigger_scrape(
    source: str,
    limit: int | None = Query(
        default=None, description="cap records pulled this run; omit to pull the whole catalog"
    ),
    session: AsyncSession = Depends(get_session),
) -> ScrapeRun:
    """Returns immediately with status="running" -- a full-catalog run can take hours.
    Poll GET /api/scrapes/{id} (or the admin panel) to watch it progress and finish, or
    POST /api/scrapes/{source}/stop to cancel it.
    """
    if source not in ADAPTERS:
        raise HTTPException(status_code=404, detail=f"unknown source, expected one of {sorted(ADAPTERS)}")
    try:
        return await start_scrape(session, source, limit=limit)
    except ScrapeAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{source}/stop", response_model=ScrapeRunOut)
async def stop_scrape_route(source: str, session: AsyncSession = Depends(get_session)) -> ScrapeRun:
    if source not in ADAPTERS:
        raise HTTPException(status_code=404, detail=f"unknown source, expected one of {sorted(ADAPTERS)}")
    run_id = stop_scrape(source)
    if run_id is None:
        raise HTTPException(status_code=404, detail=f"no {source} scrape is currently running")
    run = await session.get(ScrapeRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="scrape run not found")
    return run
