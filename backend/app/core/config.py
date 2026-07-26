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
    # Abuse protection on auth / webhook / AI endpoints. Disabled in the test
    # suite so repeated calls don't trip the limiter.
    rate_limit_enabled: bool = True

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
