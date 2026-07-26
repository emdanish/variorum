from __future__ import annotations

import httpx
import pytest

from app.models import GitHubInstallation, Repository
from app.services import slack as slack_svc
from tests.conftest import requires_db

pytestmark = requires_db

_HOOK = "https://hooks.slack.com/services/T000/B000/xyz"


def _repo(db, user_id, seq=0):
    inst = GitHubInstallation(
        installation_id=9500 + seq, account_login="acme", account_type="User",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9501 + seq, full_name=f"acme/s{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #


def test_is_valid_webhook():
    assert slack_svc.is_valid_webhook(_HOOK)
    assert not slack_svc.is_valid_webhook("")
    assert not slack_svc.is_valid_webhook("https://evil.example.com/hook")
    assert not slack_svc.is_valid_webhook("http://hooks.slack.com/x")  # must be https
    assert not slack_svc.is_valid_webhook(slack_svc.WEBHOOK_PREFIX + "y" * 600)  # too long


def test_build_digest_message():
    digest = {
        "days": 7, "new_drift": 2, "new_risk": 1, "new_knowledge": 3,
        "single_owner_modules": 4, "health_score": 72, "health_level": "fair",
        "top_hotspots": [
            {"path": "src/a.py", "score": 90}, {"path": "src/b.py", "score": 40},
        ],
    }
    msg = slack_svc.build_digest_message("acme/repo", digest)
    assert "acme/repo" in msg["text"]
    blocks = msg["blocks"]
    assert blocks[0]["type"] == "header"
    body = "".join(b["text"]["text"] for b in blocks if b["type"] == "section")
    assert "72/100" in body
    assert "src/a.py" in body
    assert "2 new doc-drift" in body


# --------------------------------------------------------------------------- #
# Config endpoints
# --------------------------------------------------------------------------- #


def test_slack_config_lifecycle(authed_client, db_session):
    api_client, user = authed_client
    assert api_client.get("/api/v1/auth/slack").json() == {"configured": False}

    bad = api_client.put("/api/v1/auth/slack", json={"webhook_url": "https://evil.com/x"})
    assert bad.status_code == 400

    ok = api_client.put("/api/v1/auth/slack", json={"webhook_url": _HOOK})
    assert ok.status_code == 200 and ok.json() == {"configured": True}
    assert api_client.get("/api/v1/auth/slack").json() == {"configured": True}
    # the secret URL is never echoed back
    assert "webhook_url" not in api_client.get("/api/v1/auth/slack").json()
    db_session.refresh(user)
    assert user.slack_webhook_url == _HOOK

    assert api_client.delete("/api/v1/auth/slack").status_code == 204
    assert api_client.get("/api/v1/auth/slack").json() == {"configured": False}


def test_slack_config_requires_auth(client):
    assert client.get("/api/v1/auth/slack").status_code == 401
    assert client.put("/api/v1/auth/slack", json={"webhook_url": _HOOK}).status_code == 401


# --------------------------------------------------------------------------- #
# Send endpoint
# --------------------------------------------------------------------------- #


def test_send_requires_configured_webhook(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, user.id, seq=0)
    db_session.flush()
    resp = api_client.post(f"/api/v1/repositories/{repo.id}/digest/slack")
    assert resp.status_code == 409


def test_send_posts_to_webhook(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    user.slack_webhook_url = _HOOK
    db_session.add(user)
    repo = _repo(db_session, user.id, seq=1)
    db_session.flush()

    sent: dict = {}

    async def fake_send(webhook_url, payload):
        sent["url"] = webhook_url
        sent["payload"] = payload

    monkeypatch.setattr("app.api.routes.repositories.slack_svc.send", fake_send)

    resp = api_client.post(f"/api/v1/repositories/{repo.id}/digest/slack", params={"days": 7})
    assert resp.status_code == 200
    assert resp.json() == {"sent": True}
    assert sent["url"] == _HOOK
    assert "blocks" in sent["payload"]


def test_send_maps_slack_error_to_502(authed_client, db_session, monkeypatch):
    import httpx

    api_client, user = authed_client
    user.slack_webhook_url = _HOOK
    db_session.add(user)
    repo = _repo(db_session, user.id, seq=2)
    db_session.flush()

    async def fake_send(webhook_url, payload):
        raise httpx.HTTPError("boom")

    monkeypatch.setattr("app.api.routes.repositories.slack_svc.send", fake_send)
    resp = api_client.post(f"/api/v1/repositories/{repo.id}/digest/slack")
    assert resp.status_code == 502


def test_send_requires_auth(client):
    assert client.post("/api/v1/repositories/1/digest/slack").status_code == 401


async def test_send_raises_on_http_error(monkeypatch):
    transport = httpx.MockTransport(lambda request: httpx.Response(500))
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(slack_svc.httpx, "AsyncClient", factory)
    with pytest.raises(httpx.HTTPStatusError):
        await slack_svc.send(_HOOK, {"text": "x"})


async def test_send_succeeds_on_2xx(monkeypatch):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text="ok"))
    original = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = transport
        return original(*args, **kwargs)

    monkeypatch.setattr(slack_svc.httpx, "AsyncClient", factory)
    await slack_svc.send(_HOOK, {"text": "x"})  # no exception == success
