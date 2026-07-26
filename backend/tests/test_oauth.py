from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from app.core.config import Settings
from app.services.github.oauth import GitHubOAuth


def _oauth(**overrides) -> GitHubOAuth:
    base = {
        "_env_file": None,
        "backend_public_url": "https://api.example.com",
        "github_app_client_id": "cid",
        "github_app_client_secret": "secret",
    }
    base.update(overrides)
    return GitHubOAuth(Settings(**base))


def test_is_configured_true_with_credentials():
    assert _oauth().is_configured() is True


def test_is_configured_false_without_credentials():
    assert _oauth(github_app_client_id="", github_app_client_secret="").is_configured() is False


def test_redirect_uri_built_from_backend_url():
    assert _oauth().redirect_uri == "https://api.example.com/api/v1/auth/github/callback"


def test_authorize_url_contains_state_and_client_id():
    url = _oauth().authorize_url("xyz-state")
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "github.com"
    assert query["client_id"] == ["cid"]
    assert query["state"] == ["xyz-state"]
    assert query["redirect_uri"] == ["https://api.example.com/api/v1/auth/github/callback"]
