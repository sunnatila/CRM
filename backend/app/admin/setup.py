from fastapi import FastAPI, Request
from sqladmin import Admin, ModelView, action
from sqladmin.authentication import AuthenticationBackend
from sqladmin.filters import AllUniqueStringValuesFilter
from sqladmin.flash import Flash
from sqlalchemy import select
from starlette.responses import RedirectResponse

from app.core.config import get_settings
from app.core.db import async_session, engine
from app.core.security import verify_password
from app.models.company import Company
from app.models.scrape_run import ScrapeRun
from app.models.user import User
from app.scrapers.pipeline import ScrapeAlreadyRunning, start_scrape, stop_scrape


class AdminAuth(AuthenticationBackend):
    """Same identity as OperatorDesk (app/api/routes/auth.py): one users table,
    one set of credentials for whoever has role="admin" -- not a separate
    hardcoded login. Session-cookie based here (SQLAdmin's own mechanism);
    OperatorDesk uses JWT for the same underlying account."""

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")
        if not username or not password:
            return False

        async with async_session() as session:
            user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()

        if user is None or user.role != "admin" or not user.is_active or not verify_password(password, user.hashed_password):
            return False

        request.session.update({"authenticated": True, "user_id": user.id})
        return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("authenticated"))


class CompanyAdmin(ModelView, model=Company):
    column_list = [
        Company.id,
        Company.source,
        Company.name,
        Company.category,
        Company.phone,
        Company.website,
        Company.address,
        Company.last_seen_at,
    ]
    column_searchable_list = [Company.name, Company.phone, Company.address]
    column_sortable_list = [Company.id, Company.source, Company.last_seen_at]
    column_filters = [AllUniqueStringValuesFilter(Company.source)]
    name = "Company"
    name_plural = "Companies"
    icon = "fa-solid fa-building"


class ScrapeRunAdmin(ModelView, model=ScrapeRun):
    column_list = [
        ScrapeRun.id,
        ScrapeRun.source,
        ScrapeRun.status,
        ScrapeRun.started_at,
        ScrapeRun.finished_at,
        ScrapeRun.records_found,
        ScrapeRun.records_upserted,
    ]
    column_sortable_list = [ScrapeRun.id, ScrapeRun.started_at]
    column_filters = [
        AllUniqueStringValuesFilter(ScrapeRun.source),
        AllUniqueStringValuesFilter(ScrapeRun.status),
    ]
    can_create = False
    can_edit = False
    name = "Scrape Run"
    name_plural = "Scrape Runs"
    icon = "fa-solid fa-rotate"

    @action(
        name="scrape_goldenpages",
        label="Scrape GoldenPages",
        add_in_detail=False,
        confirmation_message="Start a GoldenPages scrape? Only new companies are pulled -- already-scraped ones are skipped.",
    )
    async def scrape_goldenpages(self, request: Request) -> RedirectResponse:
        return await self._start(request, "goldenpages")

    @action(
        name="scrape_yellowpages",
        label="Scrape YellowPages",
        add_in_detail=False,
        confirmation_message="Start a YellowPages scrape? Only new companies are pulled -- already-scraped ones are skipped. This one is slow (headless browser per page).",
    )
    async def scrape_yellowpages(self, request: Request) -> RedirectResponse:
        return await self._start(request, "yellowpages")

    @action(
        name="stop_goldenpages",
        label="Stop GoldenPages",
        add_in_detail=False,
        confirmation_message="Stop the running GoldenPages scrape? Companies already pulled this run are kept.",
    )
    async def stop_goldenpages(self, request: Request) -> RedirectResponse:
        return await self._stop(request, "goldenpages")

    @action(
        name="stop_yellowpages",
        label="Stop YellowPages",
        add_in_detail=False,
        confirmation_message="Stop the running YellowPages scrape? Companies already pulled this run are kept.",
    )
    async def stop_yellowpages(self, request: Request) -> RedirectResponse:
        return await self._stop(request, "yellowpages")

    async def _start(self, request: Request, source: str) -> RedirectResponse:
        async with async_session() as session:
            try:
                run = await start_scrape(session, source)
            except ScrapeAlreadyRunning as exc:
                Flash.warning(request, str(exc))
            else:
                Flash.success(request, f"{source} scrape started (run #{run.id}). Refresh this page to watch it progress.")
        return RedirectResponse(request.url_for("admin:list", identity=self.identity), status_code=302)

    async def _stop(self, request: Request, source: str) -> RedirectResponse:
        run_id = stop_scrape(source)
        if run_id is None:
            Flash.warning(request, f"No {source} scrape is currently running.")
        else:
            Flash.success(request, f"Stopping {source} scrape (run #{run_id})... refresh in a moment to confirm.")
        return RedirectResponse(request.url_for("admin:list", identity=self.identity), status_code=302)


def setup_admin(app: FastAPI) -> Admin:
    settings = get_settings()
    # base_url="/sqladmin", not the sqladmin default of "/admin" -- the
    # OperatorDesk frontend's own React routes already own "/admin/*"
    # (dashboard, operators, permission-requests, claim-requests), and
    # nginx's single-origin reverse proxy (AD-10) can only route each path
    # prefix to one place.
    admin = Admin(
        app, engine, base_url="/sqladmin", authentication_backend=AdminAuth(secret_key=settings.secret_key)
    )
    admin.add_view(CompanyAdmin)
    admin.add_view(ScrapeRunAdmin)
    return admin
