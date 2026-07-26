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
