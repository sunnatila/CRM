from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from app.admin.setup import setup_admin
from app.api.routes import auth, companies, leads, notifications, operators, scrapes, ws
from app.core.config import get_settings
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


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await _bootstrap_admin()
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
