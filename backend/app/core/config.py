import logging
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Secrets that must never authenticate anything. "change-me-too" shipped as the
# code default AND in the tracked .env.example, so it is public knowledge: with
# it an attacker forges an admin JWT (whole API) or a SQLAdmin session cookie
# (edit/delete every company) without ever seeing a password. Any deployment
# still carrying one of these is treated as having no secret at all.
_REJECTED_SECRETS = frozenset({"", "change-me", "change-me-too", "secret", "changeme"})

# Written on first start when no usable SECRET_KEY was supplied. Lives on a
# Docker volume so it survives rebuilds -- a secret regenerated on every restart
# would silently log every user out and invalidate every open session.
_SECRET_FILE = Path("/app/var/secret_key")


def _resolve_secret_key(configured: str) -> str:
    """Return a real signing key, generating and persisting one if needed.

    Deliberately not "fail fast if unset": AD's deployment rule is that a bare
    `docker compose up` with no .env works out of the box, and refusing to boot
    would break that. Generating a strong key instead keeps zero-config startup
    while making the insecure default impossible to run with.
    """
    if configured.strip() not in _REJECTED_SECRETS:
        return configured

    try:
        if _SECRET_FILE.exists():
            existing = _SECRET_FILE.read_text().strip()
            if existing:
                return existing
        generated = secrets.token_hex(32)
        _SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SECRET_FILE.write_text(generated)
        _SECRET_FILE.chmod(0o600)
        logger.warning(
            "SECRET_KEY was unset or a known default; generated a new one and stored it at %s. "
            "Existing sessions and tokens are now invalid -- users must log in again.",
            _SECRET_FILE,
        )
        return generated
    except OSError as exc:
        # No writable volume (e.g. running the app straight off a checkout).
        # Still never fall back to the public default -- an ephemeral key only
        # costs a re-login on restart, whereas the default costs the whole app.
        logger.error(
            "Could not persist a generated SECRET_KEY (%s); using an in-memory one. "
            "It changes on every restart, so set SECRET_KEY explicitly for a real deployment.",
            exc,
        )
        return secrets.token_hex(32)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://parsing:parsing@postgres:5432/parsing"
    goldenpages_base_url: str = "https://www.goldenpages.uz"
    yellowpages_base_url: str = "https://www.yellowpages.uz"
    # Never read directly -- `get_settings()` replaces this with the resolved key.
    secret_key: str = ""

    # Bootstrap admin, created once on first startup if the users table is empty.
    # This one account (role="admin" in the users table) logs into both
    # OperatorDesk (JWT) and SQLAdmin (session cookie) -- a single identity.
    initial_admin_username: str = "admin"
    initial_admin_password: str = "admin123"
    initial_admin_full_name: str = "Administrator"

    cors_origins: str = "http://localhost:5173"

    # --- Scraping resilience (AD-13) ---
    # Seconds to wait between requests to the same source. The single biggest
    # lever against 429s: staying under the rate limit beats reacting to it.
    scraper_request_delay_seconds: float = 1.0
    # How many times to retry one request before giving up on it. Retries use
    # exponential backoff with jitter, and honour a 429's Retry-After header.
    scraper_max_retries: int = 4
    scraper_backoff_base_seconds: float = 2.0
    scraper_backoff_max_seconds: float = 120.0
    # How many company pages to fetch concurrently.
    #
    # Measured 2026-08-20 (12 yellowpages companies, live site):
    #   concurrency=1 -> 3.47s each
    #   concurrency=3 -> 4.83s each  (0.72x -- *slower*)
    # Raising it does not help at the default 1s delay, because every request
    # queues on the same RateLimiter anyway, so a batch costs the sum of its
    # requests while the caller waits for the whole batch before consuming any.
    # It only becomes useful alongside a much lower delay -- which these sources
    # do not tolerate. Left configurable rather than removed, defaulted to the
    # value that actually measured fastest.
    scraper_concurrency: int = 1
    # Consecutive per-item failures tolerated before aborting the whole run.
    # Isolated failures are skipped and counted; a long unbroken streak means
    # something systemic (banned, site down) and is worth stopping for.
    scraper_max_consecutive_failures: int = 25
    # Optional outbound proxies, comma-separated, rotated round-robin per
    # request (e.g. "http://user:pass@host:8080,socks5://host:1080"). Empty
    # means connect directly. Use proxies you actually control or pay for --
    # free public proxy lists are mostly dead, slow, and untrustworthy, and
    # would make this pipeline *less* reliable, not more.
    scraper_proxies: str = ""


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # Resolved once, here, so that every consumer (JWT signing in core/security,
    # the SQLAdmin session cookie in admin/setup) is guaranteed to get the same
    # real key -- and so no code path can accidentally read the placeholder.
    settings.secret_key = _resolve_secret_key(settings.secret_key)
    return settings
