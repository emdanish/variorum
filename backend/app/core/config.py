from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


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
    session_secret: str = "dev-insecure-session-secret-change-me"

    # NoDecode stops pydantic-settings from JSON-parsing the env value; the
    # validator below accepts a comma-separated string or a real list.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )

    database_url: str = "postgresql+psycopg://variorum:variorum@localhost:5432/variorum"

    gemini_api_key_1: str = ""
    gemini_api_key_2: str = ""
    deepseek_api_key: str = ""
    perplexity_api_key: str = ""

    gemini_model: str = "gemini-2.5-flash"
    deepseek_model: str = "deepseek-chat"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
