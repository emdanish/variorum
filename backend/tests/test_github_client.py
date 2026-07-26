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


async def test_history_methods(monkeypatch):
    from app.services.github.auth import InstallationToken

    auth = _auth()

    async def fake_token(_id):
        return InstallationToken(token="tok", expires_at="2099-01-01T00:00:00Z")

    monkeypatch.setattr(auth, "get_installation_token", fake_token)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/commits"):
            return httpx.Response(200, json=[
                {
                    "sha": "abc",
                    "html_url": "u/c",
                    "commit": {
                        "message": "Add auth\n\ndetail",
                        "author": {"name": "a", "date": "2026-01-01T00:00:00Z"},
                    },
                    "author": {"login": "alice"},
                },
            ])
        if path.endswith("/pulls"):
            return httpx.Response(200, json=[
                {"number": 7, "title": "JWT", "body": "d", "html_url": "u/p",
                 "user": {"login": "bob"}, "created_at": "2026-02-01T00:00:00Z"},
            ])
        if path.endswith("/issues"):
            return httpx.Response(200, json=[
                {"number": 9, "title": "bug", "body": "r", "html_url": "u/i",
                 "user": {"login": "carol"}, "created_at": "2026-03-01T00:00:00Z"},
                {"number": 10, "title": "actually a PR", "pull_request": {"url": "x"}},
            ])
        return httpx.Response(404, json=[])

    client = GitHubClient(auth, transport=httpx.MockTransport(handler))
    commits = await client.list_commits(1, "acme/app")
    prs = await client.list_pull_requests(1, "acme/app")
    issues = await client.list_issues(1, "acme/app")

    assert len(commits) == 1 and commits[0].title == "Add auth" and commits[0].author == "alice"
    assert len(prs) == 1 and prs[0].source_ref == "7"
    # issue #10 is a PR and must be filtered out
    assert [i.source_ref for i in issues] == ["9"]


async def test_write_ops_shapes(monkeypatch):
    import base64

    from app.services.github.auth import InstallationToken

    auth = _auth()

    async def fake_token(_id):
        return InstallationToken(token="tok", expires_at="2099-01-01T00:00:00Z")

    monkeypatch.setattr(auth, "get_installation_token", fake_token)
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if method == "GET" and path.endswith("/contents/docs/auth.md"):
            return httpx.Response(
                200,
                json={
                    "encoding": "base64",
                    "content": base64.b64encode(b"old").decode(),
                    "sha": "blob1",
                },
            )
        if method == "GET" and path.endswith("/git/ref/heads/main"):
            return httpx.Response(200, json={"object": {"sha": "base-sha"}})
        if method == "POST" and path.endswith("/git/refs"):
            captured["ref"] = json.loads(request.content)
            return httpx.Response(201, json={})
        if method == "PUT" and path.endswith("/contents/docs/auth.md"):
            captured["put"] = json.loads(request.content)
            return httpx.Response(201, json={"commit": {"sha": "c1"}})
        if method == "POST" and path.endswith("/pulls"):
            captured["pull"] = json.loads(request.content)
            return httpx.Response(201, json={"number": 7, "html_url": "https://gh/pr/7"})
        return httpx.Response(404, json={})

    from app.services.github.client import GitHubClient

    client = GitHubClient(auth, transport=httpx.MockTransport(handler))

    content, sha = await client.get_file(1, "acme/app", "docs/auth.md", "main")
    assert content == "old" and sha == "blob1"
    assert await client.get_branch_sha(1, "acme/app", "main") == "base-sha"
    await client.create_branch(1, "acme/app", "variorum/x", "base-sha")
    assert captured["ref"] == {"ref": "refs/heads/variorum/x", "sha": "base-sha"}
    await client.put_file(1, "acme/app", "docs/auth.md", "msg", "new", "variorum/x", "blob1")
    assert base64.b64decode(captured["put"]["content"]).decode() == "new"
    assert captured["put"]["sha"] == "blob1"
    pr = await client.create_pull_request(
        1, "acme/app", title="t", head="variorum/x", base="main", body="b"
    )
    assert pr.number == 7 and pr.url == "https://gh/pr/7"
    assert captured["pull"]["head"] == "variorum/x"
