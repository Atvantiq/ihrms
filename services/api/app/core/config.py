from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings, loaded from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Atvantiq People API"
    environment: str = "dev"
    tenant_id: str = "atvantiq"

    # Postgres (Supabase session pooler; direct host is IPv6-only)
    database_url: str = ""
    # Async URL derived for SQLAlchemy if not set explicitly
    database_url_async: str = ""

    # Supabase Auth (shared with ONAQT — one login for both apps)
    supabase_url: str = ""
    supabase_jwt_secret: str = ""

    # DEV ONLY — lets endpoints run before Supabase keys are wired
    auth_disabled: bool = False

    # Comma-separated origins for the web app
    cors_origins: str = "http://localhost:3000"

    @property
    def sqlalchemy_async_url(self) -> str:
        if self.database_url_async:
            return self.database_url_async
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
