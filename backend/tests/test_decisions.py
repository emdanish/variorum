from __future__ import annotations

from datetime import UTC, datetime

from app.models import (
    DecisionEntry,
    GitHubInstallation,
    KnowledgeEntry,
    KnowledgeKind,
    Repository,
)
from app.services import decisions as svc
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


class _Embedder:
    """Stub embedder: fixed-dimension vectors, one per input text."""

    def __init__(self, available=True):
        self._available = available

    @property
    def available(self) -> bool:
        return self._available

    def embed(self, _text):
        return [1.0, 0.0]

    def embed_batch(self, texts):
        return [[float(i + 1), 0.0] for i, _ in enumerate(texts)]


def _entries():
    return [
        KnowledgeEntry(
            repository_id=1, kind=KnowledgeKind.pull_request, source_ref="182",
            title="Add Redis queue", body="APIs timed out under load.", url="http://x/182",
            occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
        ),
        KnowledgeEntry(
            repository_id=1, kind=KnowledgeKind.commit, source_ref="abc",
            title="tweak", body="minor", occurred_at=datetime(2026, 3, 2, tzinfo=UTC),
        ),
    ]


def test_parse_resolves_citations_and_dates():
    entries = _entries()
    data = {
        "decisions": [
            {"title": "Introduce Redis queues", "summary": "Moved async work off the request path.",
             "cited": [1]},
            {"title": "no summary -> dropped", "summary": "", "cited": [1]},
            {"title": "bad cite", "summary": "s", "cited": [99]},
        ]
    }
    parsed = svc._parse(data, entries)
    assert len(parsed) == 2  # empty-summary dropped; bad-cite kept (0 sources)
    first = parsed[0]
    assert first["title"] == "Introduce Redis queues"
    assert first["sources"][0]["ref"] == "182"
    assert first["sources"][0]["url"] == "http://x/182"
    assert first["decided_at"] == datetime(2026, 3, 1, tzinfo=UTC)


def test_parse_handles_garbage():
    assert svc._parse({}, _entries()) == []
    assert svc._parse({"decisions": "nope"}, _entries()) == []


def _seed(db, user_id, seq=0) -> Repository:
    inst = GitHubInstallation(
        installation_id=9700 + seq, account_login="acme", account_type="User",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9701 + seq, full_name=f"acme/d{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def test_generate_and_list_decisions_endpoint(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo = _seed(db_session, user.id)
    db_session.add(
        KnowledgeEntry(
            repository_id=repo.id, kind=KnowledgeKind.pull_request, source_ref="5",
            title="Adopt JWT", body="Replaced sessions with JWT for stateless auth.",
            url="http://x/5", occurred_at=datetime(2026, 2, 1, tzinfo=UTC),
        )
    )
    db_session.flush()

    fake = FakeAI(
        verdict={
            "decisions": [
                {"title": "Adopt JWT auth", "summary": "Stateless auth via JWT.", "cited": [1]}
            ]
        }
    )
    monkeypatch.setattr("app.api.routes.repositories.get_ai_service", lambda: fake)

    resp = api_client.post(f"/api/v1/repositories/{repo.id}/decisions")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Adopt JWT auth"
    assert data[0]["sources"][0]["ref"] == "5"

    got = api_client.get(f"/api/v1/repositories/{repo.id}/decisions")
    assert got.status_code == 200
    assert got.json()[0]["title"] == "Adopt JWT auth"


def test_generate_decisions_409_without_history(authed_client, db_session):
    api_client, user = authed_client
    repo = _seed(db_session, user.id, seq=1)
    db_session.flush()
    assert api_client.post(f"/api/v1/repositories/{repo.id}/decisions").status_code == 409


def test_decisions_require_auth(client):
    assert client.get("/api/v1/repositories/1/decisions").status_code == 401
    assert client.post("/api/v1/repositories/1/decisions").status_code == 401


def test_replace_decisions_embeds_when_embedder_available(db_session):
    u_repo = _seed(db_session, _new_user(db_session), seq=2)
    decisions = [
        {"title": "Use Redis", "summary": "Async off the request path.", "sources": [],
         "decided_at": None},
        {"title": "Adopt JWT", "summary": "Stateless auth.", "sources": [], "decided_at": None},
    ]
    n = svc.replace_decisions(
        db_session, u_repo.id, decisions, provider="p", model="m", embedder=_Embedder()
    )
    assert n == 2
    rows = db_session.query(DecisionEntry).filter_by(repository_id=u_repo.id).all()
    assert all(r.embedding is not None for r in rows)


def test_replace_decisions_leaves_embedding_null_without_embedder(db_session):
    repo = _seed(db_session, _new_user(db_session), seq=3)
    n = svc.replace_decisions(
        db_session, repo.id,
        [{"title": "t", "summary": "s", "sources": [], "decided_at": None}],
        provider=None, model=None,
    )
    assert n == 1
    row = db_session.query(DecisionEntry).filter_by(repository_id=repo.id).one()
    assert row.embedding is None


def test_embed_missing_decisions_backfills(db_session):
    repo = _seed(db_session, _new_user(db_session), seq=4)
    svc.replace_decisions(
        db_session, repo.id,
        [{"title": "t", "summary": "s", "sources": [], "decided_at": None}],
        provider=None, model=None,
    )
    assert svc.embed_missing_decisions(db_session, repo.id, _Embedder()) == 1
    row = db_session.query(DecisionEntry).filter_by(repository_id=repo.id).one()
    assert row.embedding is not None
    # idempotent: nothing left to embed on a second pass
    assert svc.embed_missing_decisions(db_session, repo.id, _Embedder()) == 0
    # unavailable embedder is a no-op
    assert svc.embed_missing_decisions(db_session, repo.id, _Embedder(available=False)) == 0


def _new_user(db):
    from app.models import User

    u = User(email=f"dec{db.query(User).count()}@example.com")
    db.add(u)
    db.flush()
    return u.id
