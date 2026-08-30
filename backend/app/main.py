import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update

from app.admin.setup import setup_admin
from app.api.routes import auth, companies, leads, notifications, operators, scrapes, ws
from app.core.config import get_settings
from app.models.scrape_run import ScrapeRun
from app.services.leads import LeadError
from app.core.db import async_session
from app.core.security import hash_password
from app.models.user import User


async def _bootstrap_admin() -> None:
    settings = get_settings()
    async with async_session() as session:
        existing = (await session.execute(select(User).limit(1))).scalar_one_or_none()
        if existing is not None:
            return
        session.add(
            User(
                username=settings.initial_admin_username,
                hashed_password=hash_password(settings.initial_admin_password),
                full_name=settings.initial_admin_full_name,
                role="admin",
            )
        )
        await session.commit()


async def _reap_orphaned_scrape_runs() -> None:
    """Close out runs left "running" by a process that is no longer alive.

    A scrape lives as an asyncio task in THIS process, tracked in an in-memory
    dict -- so immediately after startup, by definition, nothing is running. Any
    row still marked `running` belongs to a previous process that was killed
    (container rebuild, OOM, `compose down`), where no Python handler could
    possibly have run to record the ending.

    Without this the rows lie forever: the admin panel shows a scrape "running"
    for days, `POST /scrapes/{source}/stop` 404s because the task registry is
    empty, and the only fix is a manual UPDATE. Reaping them at boot is the one
    moment we can be certain the claim is false.
    """
    async with async_session() as session:
        result = await session.execute(
            update(ScrapeRun)
            .where(ScrapeRun.status == "running")
            .values(
                status="stopped",
                finished_at=datetime.now(UTC),
                error_message="Jarayon to'xtatildi (server qayta ishga tushdi).",
            )
        )
        await session.commit()
        if result.rowcount:
            logging.getLogger(__name__).warning(
                "reaped %d scrape run(s) left 'running' by a previous process", result.rowcount
            )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await _bootstrap_admin()
    await _reap_orphaned_scrape_runs()
    yield


app = FastAPI(title="Parsing Project Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(LeadError)
async def _lead_error_handler(_request: Request, exc: LeadError) -> JSONResponse:
    """One place turns a domain refusal into HTTP, so every /leads route answers
    in the same {code, message, ...context} shape (AR-13). `message` is already
    operator-facing Uzbek -- the frontend shows it verbatim."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.as_detail()})


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(companies.router, prefix="/api")
app.include_router(scrapes.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(operators.router, prefix="/api")
app.include_router(ws.router, prefix="/api")
app.include_router(leads.router, prefix="/api")

setup_admin(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
