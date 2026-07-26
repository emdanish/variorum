from __future__ import annotations

from app.models import GitHubInstallation, IndexingStatus, Repository
from tests.conftest import requires_db

pytestmark = requires_db


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_repositories_requires_auth(client):
    assert client.get("/api/v1/repositories").status_code == 401


def test_me_returns_current_user(authed_client):
    api_client, user = authed_client
    resp = api_client.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == user.email


def _seed_repo(db, user_id: int) -> Repository:
    inst = GitHubInstallation(
        installation_id=7001,
        account_login="acme",
        account_type="Organization",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id,
        github_repo_id=42,
        full_name="acme/api",
        default_branch="main",
        private=True,
    )
    db.add(repo)
    db.flush()
    return repo


def test_repositories_listed_scoped_to_user(authed_client, db_session):
    api_client, user = authed_client
    _seed_repo(db_session, user.id)
    resp = api_client.get("/api/v1/repositories")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["full_name"] == "acme/api"
    assert body[0]["indexing_status"] == "pending"


def test_connect_repository_queues_indexing(authed_client, db_session):
    api_client, user = authed_client
    repo = _seed_repo(db_session, user.id)
    repo.indexing_status = IndexingStatus.indexed
    db_session.flush()

    resp = api_client.post(f"/api/v1/repositories/{repo.id}/connect")
    assert resp.status_code == 200
    assert resp.json()["indexing_status"] == "pending"


def test_connect_unknown_repository_404(authed_client):
    api_client, _ = authed_client
    assert api_client.post("/api/v1/repositories/999999/connect").status_code == 404
