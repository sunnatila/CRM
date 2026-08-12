from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models.scrape_run import ScrapeRun
from app.schemas.company import ScrapeRunOut
from app.scrapers.pipeline import ADAPTERS, ScrapeAlreadyRunning, start_scrape, stop_scrape

router = APIRouter(prefix="/scrapes", tags=["scrapes"])


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
