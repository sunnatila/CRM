from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://parsing:parsing@postgres:5432/parsing"
    goldenpages_base_url: str = "https://www.goldenpages.uz"
    yellowpages_base_url: str = "https://www.yellowpages.uz"
    secret_key: str = "change-me-too"

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
    return Settings()
