from __future__ import annotations

from app.models import GitHubInstallation, Repository
from tests.conftest import requires_db

pytestmark = requires_db


def test_system_status_shape(client):
    resp = client.get("/api/v1/system/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["database"] == "ok"
    assert isinstance(body["ai_available"], bool)
    assert isinstance(body["ai_providers"], list)
    assert set(body["github_app"]) >= {
        "app_id",
        "private_key",
        "webhook_secret",
        "oauth",
        "configured",
    }


def test_analyze_pr_requires_auth(client):
    resp = client.post("/api/v1/repositories/1/analyze-pr", json={"pr_number": 1})
    assert resp.status_code == 401


def test_analyze_pr_enqueues_job(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    inst = GitHubInstallation(
        installation_id=9200, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db_session.add(inst)
    db_session.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9201, full_name="acme/app", default_branch="main"
    )
    db_session.add(repo)
    db_session.flush()

    calls: list[tuple] = []
    monkeypatch.setattr(
        "app.api.routes.repositories.run_pr_analysis_job",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    resp = api_client.post(f"/api/v1/repositories/{repo.id}/analyze-pr", json={"pr_number": 77})
    assert resp.status_code == 202
    assert resp.json() == {"status": "queued", "repository_id": repo.id, "pr_number": 77}
    assert calls and calls[0][0] == (repo.id, 77)


def test_analyze_pr_unknown_repo_404(authed_client):
    api_client, _ = authed_client
    resp = api_client.post("/api/v1/repositories/999999/analyze-pr", json={"pr_number": 1})
    assert resp.status_code == 404
