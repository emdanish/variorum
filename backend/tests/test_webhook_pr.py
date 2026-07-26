from __future__ import annotations

import json

from app.models import GitHubInstallation, Repository, User
from tests.conftest import requires_db

pytestmark = requires_db


def _seed_repo(db, github_repo_id: int) -> Repository:
    user = User(email="wh@example.com", github_user_id=222)
    db.add(user)
    db.flush()
    inst = GitHubInstallation(
        installation_id=6600, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id,
        github_repo_id=github_repo_id,
        full_name="acme/app",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def _payload(action: str, repo_id: int, number: int) -> bytes:
    return json.dumps(
        {
            "action": action,
            "pull_request": {"number": number, "head": {"sha": "deadbeef"}},
            "repository": {"id": repo_id},
        }
    ).encode()


def _patch(monkeypatch):
    calls: list[tuple] = []
    risk_calls: list[tuple] = []
    monkeypatch.setattr(
        "app.api.routes.webhooks.verify_webhook_signature", lambda *a, **k: True
    )
    monkeypatch.setattr(
        "app.api.routes.webhooks.run_pr_analysis_job",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr(
        "app.api.routes.webhooks.run_risk_analysis_job",
        lambda *args, **kwargs: risk_calls.append((args, kwargs)),
    )
    return calls, risk_calls


def test_pull_request_opened_enqueues_analysis(client, db_session, monkeypatch):
    calls, risk_calls = _patch(monkeypatch)
    repo = _seed_repo(db_session, 5501)

    resp = client.post(
        "/webhooks/github",
        content=_payload("opened", 5501, 7),
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=x"},
    )
    assert resp.status_code == 202
    assert resp.json()["result"] == "pr_analysis:queued:7"
    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == (repo.id, 7)
    assert kwargs["head_sha"] == "deadbeef"
    # Unified flow: risk analysis is enqueued too.
    assert risk_calls and risk_calls[0][0] == (repo.id, 7)


def test_pull_request_closed_is_skipped(client, db_session, monkeypatch):
    calls, risk_calls = _patch(monkeypatch)
    _seed_repo(db_session, 5502)

    resp = client.post(
        "/webhooks/github",
        content=_payload("closed", 5502, 8),
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=x"},
    )
    assert resp.json()["result"] == "pr_analysis:skipped"
    assert calls == [] and risk_calls == []


def test_pull_request_unknown_repo_is_skipped(client, db_session, monkeypatch):
    calls, risk_calls = _patch(monkeypatch)

    resp = client.post(
        "/webhooks/github",
        content=_payload("opened", 999999, 9),
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": "sha256=x"},
    )
    assert resp.json()["result"] == "pr_analysis:skipped"
    assert calls == [] and risk_calls == []
