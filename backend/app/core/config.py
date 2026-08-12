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


@lru_cache
def get_settings() -> Settings:
    return Settings()
