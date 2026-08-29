"""Test fixtures for the lead state machine.

Runs against a real PostgreSQL, not SQLite: the claim race depends on
`INSERT ... ON CONFLICT DO UPDATE ... WHERE` and the queue on `DISTINCT ON`.
Testing that logic on a different engine would prove nothing about the one it
actually runs on.
"""

import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from app.core.db import Base
from app.models import Company, LeadEvent, LeadState, User  # noqa: F401 -- registers metadata
from app.models.review import CompanyReview

# Points at the compose Postgres by default; override to run elsewhere.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://parsing:parsing@localhost:5433/parsing_test"
)


@pytest_asyncio.fixture(scope="session")
async def engine():
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    db_name = TEST_DATABASE_URL.rsplit("/", 1)[1]

    # CREATE DATABASE cannot run inside a transaction block.
    admin = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        exists = await conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name})
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    await admin.dispose()

    eng = create_async_engine(TEST_DATABASE_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncSession:
    """A clean slate per test -- the state machine is all about ordering, and a
    leftover row from a previous test would make failures look like flakes."""
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        for table in ("lead_events", "lead_states", "company_reviews", "companies", "users"):
            await s.execute(text(f"TRUNCATE {table} RESTART IDENTITY CASCADE"))
        await s.commit()
        yield s


@pytest_asyncio.fixture
async def session_factory(engine):
    """For tests that need two independent sessions -- the claim race needs two
    real connections, not two identity maps over one."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def make_user(session: AsyncSession, username: str, role: str = "operator") -> User:
    user = User(username=username, hashed_password="x", full_name=username.title(), role=role)
    session.add(user)
    await session.flush()
    return user


async def make_company(session: AsyncSession, name: str = "Test Co", source_id: str = "1") -> Company:
    company = Company(source="test", source_id=source_id, name=name)
    session.add(company)
    await session.flush()
    return company


async def set_fields(session: AsyncSession, company_id: int, website: bool | None, lms: bool | None) -> None:
    for field, value in (("website", website), ("lms", lms)):
        session.add(CompanyReview(company_id=company_id, field=field, available=value))
    await session.flush()
