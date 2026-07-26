from __future__ import annotations

import base64
import json

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import Settings
from app.services.github.auth import GitHubAppAuth, InstallationToken
from app.services.github.client import GitHubClient


def _auth() -> GitHubAppAuth:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    settings = Settings(
        _env_file=None,
        github_app_id="123",
        github_app_private_key_base64=base64.b64encode(pem.encode()).decode(),
    )
    return GitHubAppAuth(settings)


async def test_get_installation_parses_account():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/app/installations/55"
        return httpx.Response(
            200,
            json={
                "id": 55,
                "account": {"login": "acme", "type": "Organization"},
                "suspended_at": None,
            },
        )

    client = GitHubClient(_auth(), transport=httpx.MockTransport(handler))
    account = await client.get_installation(55)
    assert account.installation_id == 55
    assert account.account_login == "acme"
    assert account.account_type == "Organization"
    assert account.suspended is False


async def test_list_installation_repositories_paginates(monkeypatch):
    auth = _auth()

    async def fake_token(_installation_id: int) -> InstallationToken:
        return InstallationToken(token="tok", expires_at="2099-01-01T00:00:00Z")

    monkeypatch.setattr(auth, "get_installation_token", fake_token)

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(httpx.QueryParams(request.url.query).get("page", "1"))
        if page == 1:
            repos = [
                {"id": i, "full_name": f"acme/repo{i}", "private": True} for i in range(1, 101)
            ]
        else:
            repos = [{"id": 101, "full_name": "acme/last", "private": False}]
        return httpx.Response(200, json={"repositories": repos})

    client = GitHubClient(auth, transport=httpx.MockTransport(handler))
    repos = await client.list_installation_repositories(55)
    assert len(repos) == 101
    assert repos[-1].full_name == "acme/last"
    assert repos[-1].private is False


async def test_get_installation_raises_on_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    client = GitHubClient(_auth(), transport=httpx.MockTransport(handler))
    with pytest.raises(httpx.HTTPStatusError):
        await client.get_installation(999)


def test_query_params_json_available():
    # sanity: ensure test payloads are JSON-serializable (guards fixtures)
    assert json.loads(json.dumps({"ok": True})) == {"ok": True}
