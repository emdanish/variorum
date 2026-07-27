from __future__ import annotations

from app.core.config import Settings


def test_cors_origins_parsed_from_comma_string():
    settings = Settings(_env_file=None, cors_origins="http://a.com, http://b.com ,http://c.com")
    assert settings.cors_origins == ["http://a.com", "http://b.com", "http://c.com"]


def test_cors_origins_accepts_list():
    settings = Settings(_env_file=None, cors_origins=["http://a.com"])
    assert settings.cors_origins == ["http://a.com"]


def test_is_production_flag():
    assert Settings(_env_file=None, environment="production").is_production is True
    assert Settings(_env_file=None, environment="development").is_production is False


def test_defaults_are_safe_without_env():
    settings = Settings(_env_file=None)
    assert settings.app_name == "Variorum"
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_managed_postgres_url_normalized_to_psycopg():
    # Providers (Neon/Render/Supabase/Railway) hand out postgres:// / postgresql://
    for scheme in ("postgresql://", "postgres://"):
        s = Settings(_env_file=None, database_url=f"{scheme}u:p@host/db?sslmode=require")
        assert s.database_url == "postgresql+psycopg://u:p@host/db?sslmode=require"
    # an explicit driver is left untouched
    already = "postgresql+psycopg://u:p@localhost:5432/variorum"
    assert Settings(_env_file=None, database_url=already).database_url == already


def test_production_flags_missing_secrets():
    issues = Settings(_env_file=None, environment="production").production_security_issues()
    text = " ".join(issues)
    # Defaults leave these insecure → must be flagged before a prod launch.
    assert "SESSION_SECRET" in text
    assert "DATABASE_URL" in text
    assert "GITHUB_WEBHOOK_SECRET" in text
    # A wildcard CORS origin must be rejected when credentials are sent.
    wild = Settings(
        _env_file=None, environment="production", cors_origins="*"
    ).production_security_issues()
    assert any("CORS_ORIGINS" in i for i in wild)
