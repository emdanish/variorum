from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_SESSION_SECRET = "dev-insecure-session-secret-change-me"
DEFAULT_DATABASE_URL = "postgresql+psycopg://variorum:variorum@localhost:5432/variorum"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    app_name: str = "Variorum"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_public_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    session_secret: str = DEFAULT_SESSION_SECRET
    # Session cookie SameSite policy. Use "lax" for same-site (local dev or a
    # same-origin proxy). For a split-domain deploy (frontend and backend on
    # different origins) set "none" — the cookie is then only sent over HTTPS
    # (Secure is enabled automatically in production).
    session_cookie_samesite: str = "lax"
    # Abuse protection on auth / webhook / AI endpoints. Disabled in the test
    # suite so repeated calls don't trip the limiter.
    rate_limit_enabled: bool = True

    # In-process weekly-digest scheduler (Slack delivery). Runs a background loop
    # that ticks every `scheduler_interval_seconds`. Disabled in the test suite.
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 900

    # Per-user AI credit meter. Variorum runs on free-tier AI keys shared across
    # every tenant, so each user gets a generous daily allotment of AI actions
    # (ask, PR analysis, generated PRs, briefings, orientation). The allotment
    # refreshes automatically once `credit_window_seconds` elapses.
    user_daily_credits: int = 150
    credit_window_seconds: int = 86_400  # 24h
    # A fleet-wide daily ceiling on AI actions across ALL users — a hard stop
    # that protects the shared free-tier quota once the day's budget is spent,
    # regardless of any single user's remaining allotment.
    global_daily_credits: int = 1_000

    # SQLAlchemy connection pool sizing (per process). Tune against the
    # database's max_connections and the number of running replicas.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 1800

    # NoDecode stops pydantic-settings from JSON-parsing the env value; the
    # validator below accepts a comma-separated string or a real list.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    database_url: str = DEFAULT_DATABASE_URL

    gemini_api_key_1: str = ""
    gemini_api_key_2: str = ""
    deepseek_api_key: str = ""
    perplexity_api_key: str = ""

    # Use the pgvector acceleration path for semantic search when the extension
    # and column are present. Set false to force the in-process cosine fallback.
    pgvector_enabled: bool = True

    gemini_model: str = "gemini-flash-latest"
    deepseek_model: str = "deepseek-v4-flash"
    perplexity_model: str = "sonar"

    github_app_id: str = ""
    github_app_slug: str = ""
    github_app_client_id: str = ""
    github_app_client_secret: str = ""
    github_webhook_secret: str = ""
    github_app_private_key_path: str = "./secrets/github-app.pem"
    github_app_private_key_base64: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_db_url(cls, value: object) -> object:
        """Coerce a managed-Postgres URL to the psycopg (v3) driver. Providers
        (Neon, Render, Supabase, Railway) hand out ``postgres://`` /
        ``postgresql://`` URLs, which SQLAlchemy would route to the uninstalled
        psycopg2 dialect. Rewriting the scheme lets the provider URL be pasted
        verbatim into DATABASE_URL."""
        if isinstance(value, str):
            for scheme in ("postgresql://", "postgres://"):
                if value.startswith(scheme):
                    return "postgresql+psycopg://" + value[len(scheme):]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    def production_security_issues(self) -> list[str]:
        """Return misconfigurations that must be fixed before a production launch.

        Empty list means the security-critical config is sound. Callers should
        refuse to start (or loudly warn) in production when this is non-empty.
        """
        issues: list[str] = []
        if not self.session_secret or self.session_secret == DEFAULT_SESSION_SECRET:
            issues.append(
                "SESSION_SECRET must be set to a strong random value (it signs auth "
                "session cookies)."
            )
        if not self.github_webhook_secret:
            issues.append(
                "GITHUB_WEBHOOK_SECRET must be set so inbound webhooks can be verified."
            )
        if self.database_url == DEFAULT_DATABASE_URL:
            issues.append("DATABASE_URL must not use the default local dev credentials.")
        if not self.cors_origins or "*" in self.cors_origins:
            issues.append(
                "CORS_ORIGINS must be an explicit allowlist of frontend URLs, never '*' "
                "(credentials are sent with cross-origin requests)."
            )
        return issues


@lru_cache
def get_settings() -> Settings:
    return Settings()
