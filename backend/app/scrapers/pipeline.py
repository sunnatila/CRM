from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import async_session
from app.models.company import Company
from app.models.scrape_run import ScrapeRun
from app.scrapers.base import CompanyIn, SourceAdapter
from app.scrapers.goldenpages.adapter import GoldenPagesAdapter
from app.scrapers.yellowpages.adapter import YellowPagesAdapter

ADAPTERS: dict[str, type[SourceAdapter]] = {
    "goldenpages": GoldenPagesAdapter,
    "yellowpages": YellowPagesAdapter,
}

_PROGRESS_COMMIT_EVERY = 20

# One entry-point (admin button or API call) per source at a time -- shared across both,
# since they end up in the same process. Lets a caller cancel a run it didn't start.
_RUNNING_TASKS: dict[str, tuple[int, asyncio.Task]] = {}


class ScrapeAlreadyRunning(Exception):
    def __init__(self, source: str, run_id: int) -> None:
        self.source = source
        self.run_id = run_id
        super().__init__(f"{source} scrape already running (run #{run_id})")


def get_running_run_id(source: str) -> int | None:
    entry = _RUNNING_TASKS.get(source)
    return entry[0] if entry else None


async def start_scrape(session: AsyncSession, source: str, *, limit: int | None = None) -> ScrapeRun:
    """Create the ScrapeRun row and launch the actual scrape as a cancellable background
    task. Raises ScrapeAlreadyRunning if this source already has one in flight."""
    if source not in ADAPTERS:
        raise ValueError(f"unknown source: {source!r}, expected one of {sorted(ADAPTERS)}")

    running_id = get_running_run_id(source)
    if running_id is not None:
        raise ScrapeAlreadyRunning(source, running_id)

    run = ScrapeRun(source=source, started_at=datetime.now(UTC), status="running")
    session.add(run)
    await session.commit()
    await session.refresh(run)

    task = asyncio.create_task(_run_in_background(run.id, source, limit))
    _RUNNING_TASKS[source] = (run.id, task)
    task.add_done_callback(lambda _t, s=source: _RUNNING_TASKS.pop(s, None))

    return run


def stop_scrape(source: str) -> int | None:
    """Cancel the in-flight task for source, if any. Returns the run_id being stopped."""
    entry = _RUNNING_TASKS.get(source)
    if entry is None:
        return None
    run_id, task = entry
    task.cancel()
    return run_id


async def _run_in_background(run_id: int, source: str, limit: int | None) -> None:
    async with async_session() as session:
        await run_adapter(session, source, run_id=run_id, limit=limit)


async def run_adapter(
    session: AsyncSession, source: str, *, run_id: int | None = None, limit: int | None = None
) -> ScrapeRun:
    """A company already in our DB for this source is skipped entirely -- not re-fetched,
    not re-visited. This keeps repeat runs cheap and avoids hammering the sites for data
    we already have; it does mean an existing company's details never refresh via a normal
    run (only newly-discovered companies are pulled).

    limit caps how many *new* records are pulled in this run (useful for manual/partial
    runs); None means "as many as the adapter yields" (the whole remaining catalog).

    run_id: update a ScrapeRun row already created (by the caller, in its own session --
    e.g. a background task) instead of creating a new one. Progress (records_found/
    records_upserted) is committed periodically, not just at the end, so a long run's
    status is visible mid-flight (GET /api/scrapes/{id}, or the admin panel).
    """
    if source not in ADAPTERS:
        raise ValueError(f"unknown source: {source!r}, expected one of {sorted(ADAPTERS)}")

    adapter = ADAPTERS[source]()
    if run_id is not None:
        run = await session.get(ScrapeRun, run_id)
        if run is None:
            raise ValueError(f"scrape run {run_id} not found")
    else:
        run = ScrapeRun(source=source, started_at=datetime.now(UTC), status="running")
        session.add(run)
        await session.flush()

    skip_ids = set(
        (await session.execute(select(Company.source_id).where(Company.source == source))).scalars().all()
    )

    found = 0
    upserted = 0
    try:
        async for raw in adapter.fetch_raw(skip_ids=skip_ids):
            found += 1
            company_in = adapter.normalize(raw)
            await _upsert_company(session, company_in)
            upserted += 1
            if found % _PROGRESS_COMMIT_EVERY == 0:
                run.records_found = found
                run.records_upserted = upserted
                await session.commit()
            if limit is not None and found >= limit:
                break
        run.status = "success"
    except asyncio.CancelledError:
        run.status = "stopped"
        raise
    except Exception as exc:  # noqa: BLE001 -- captured on the run row, not swallowed silently
        run.status = "failed"
        run.error_message = str(exc)[:2000]
    finally:
        run.records_found = found
        run.records_upserted = upserted
        run.finished_at = datetime.now(UTC)
        await session.commit()

    return run


async def _upsert_company(session: AsyncSession, company_in: CompanyIn) -> Company:
    stmt = select(Company).where(
        Company.source == company_in.source,
        Company.source_id == company_in.source_id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()

    if existing is None:
        company = Company(**company_in.model_dump())
        session.add(company)
        await session.flush()
        return company

    for field, value in company_in.model_dump().items():
        if field in ("source", "source_id"):
            continue
        setattr(existing, field, value)
    await session.flush()
    return existing
