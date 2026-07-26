from __future__ import annotations

from sqlalchemy import func, select

from app.models import GitHubInstallation, KnowledgeEntry, KnowledgeKind, Repository, User
from app.services.github.client import HistoryItem
from app.services.knowledge import store_items
from app.workers.ingest import run_ingest_history_job
from tests.conftest import requires_db

pytestmark = requires_db


def _seed_repo(db, *, owner_id: int | None = None) -> Repository:
    user_id = owner_id
    if user_id is None:
        user = User(email="kn@example.com", github_user_id=6001)
        db.add(user)
        db.flush()
        user_id = user.id
    inst = GitHubInstallation(
        installation_id=8500, account_login="acme", account_type="User", owner_user_id=user_id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8501, full_name="acme/app", default_branch="main"
    )
    db.add(repo)
    db.flush()
    return repo


def _items() -> list[HistoryItem]:
    return [
        HistoryItem("commit", "abc123", "Add auth", "Add auth\n\nbody", "u/1", "alice",
                    "2026-01-01T00:00:00Z"),
        HistoryItem("pull_request", "7", "Switch to JWT", "desc", "u/2", "bob",
                    "2026-02-01T00:00:00Z"),
        HistoryItem("issue", "9", "Cookie bug", "repro", "u/3", "carol",
                    "2026-03-01T00:00:00Z"),
    ]


def test_store_items_is_idempotent(db_session):
    repo = _seed_repo(db_session)
    assert store_items(db_session, repo.id, _items()) == 3
    # Re-store the same commit with an updated title -> update, not duplicate.
    store_items(
        db_session,
        repo.id,
        [HistoryItem("commit", "abc123", "Add auth (edited)", "b", "u/1", "alice", None)],
    )
    total = db_session.scalar(
        select(func.count()).select_from(KnowledgeEntry).where(
            KnowledgeEntry.repository_id == repo.id
        )
    )
    assert total == 3
    commit = db_session.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.repository_id == repo.id, KnowledgeEntry.kind == KnowledgeKind.commit
        )
    ).scalar_one()
    assert commit.title == "Add auth (edited)"


def test_run_ingest_history_job_with_items(db_session):
    repo = _seed_repo(db_session)
    stored = run_ingest_history_job(repo.id, db=db_session, items=_items())
    assert stored == 3
    kinds = set(
        db_session.execute(
            select(KnowledgeEntry.kind).where(KnowledgeEntry.repository_id == repo.id)
        ).scalars()
    )
    assert kinds == {KnowledgeKind.commit, KnowledgeKind.pull_request, KnowledgeKind.issue}


def test_run_ingest_missing_repo_returns_none(db_session):
    assert run_ingest_history_job(10_000_000, db=db_session, items=_items()) is None


def test_ingest_endpoint_enqueues(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo = _seed_repo(db_session, owner_id=user.id)
    calls: list[tuple] = []
    monkeypatch.setattr(
        "app.api.routes.repositories.run_ingest_history_job",
        lambda *a, **k: calls.append((a, k)),
    )
    resp = api_client.post(f"/api/v1/repositories/{repo.id}/ingest-history")
    assert resp.status_code == 202
    assert resp.json() == {"status": "queued", "repository_id": repo.id}
    assert calls and calls[0][0] == (repo.id,)


def test_knowledge_stats_endpoint(authed_client, db_session):
    api_client, user = authed_client
    repo = _seed_repo(db_session, owner_id=user.id)
    store_items(db_session, repo.id, _items())
    resp = api_client.get(f"/api/v1/repositories/{repo.id}/knowledge/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert body["by_kind"] == {"commit": 1, "pull_request": 1, "issue": 1}


def test_ingest_endpoint_requires_auth(client):
    assert client.post("/api/v1/repositories/1/ingest-history").status_code == 401
