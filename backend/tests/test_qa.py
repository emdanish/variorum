from __future__ import annotations

from app.models import GitHubInstallation, KnowledgeEntry, KnowledgeKind, Repository, User
from app.services.knowledge import embed_missing
from app.services.qa import answer_question, retrieve
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


class FakeEmbedder:
    """Returns a fixed query vector, and per-text vectors for batches."""

    def __init__(self, query_vec, batch_vecs=None):
        self._query_vec = query_vec
        self._batch_vecs = batch_vecs

    @property
    def available(self) -> bool:
        return True

    def embed(self, _text):
        return self._query_vec

    def embed_batch(self, texts):
        return self._batch_vecs or [[1.0, 0.0] for _ in texts]


def _seed(db, *, owner_id: int | None = None) -> Repository:
    uid = owner_id
    if uid is None:
        u = User(email="qa@example.com", github_user_id=7100)
        db.add(u)
        db.flush()
        uid = u.id
    inst = GitHubInstallation(
        installation_id=8600, account_login="acme", account_type="User", owner_user_id=uid
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8601, full_name="acme/app", default_branch="main"
    )
    db.add(repo)
    db.flush()
    entries = [
        KnowledgeEntry(
            repository_id=repo.id, kind=KnowledgeKind.pull_request, source_ref="182",
            title="Introduce Redis queues", body="API requests were timing out; add Redis queues.",
            url="https://gh/pr/182", author="priya",
        ),
        KnowledgeEntry(
            repository_id=repo.id, kind=KnowledgeKind.commit, source_ref="deadbeef",
            title="Update styling", body="tweak CSS variables", url="https://gh/c/deadbeef",
            author="sam",
        ),
    ]
    db.add_all(entries)
    db.flush()
    return repo


def test_retrieve_finds_relevant(db_session):
    repo = _seed(db_session)
    hits = retrieve(db_session, repo.id, "why redis queues")
    assert hits
    assert hits[0].source_ref == "182"


def test_retrieve_empty_on_no_match(db_session):
    repo = _seed(db_session)
    assert retrieve(db_session, repo.id, "kubernetes helm sharding") == []


def test_hybrid_retrieval_finds_semantically_close_without_keywords(db_session):
    repo = _seed(db_session)
    # Two embedded entries; the question shares NO keywords with either.
    e1 = KnowledgeEntry(
        repository_id=repo.id, kind=KnowledgeKind.commit, source_ref="c1",
        title="gamma", body="gamma", embedding=[1.0, 0.0, 0.0],
    )
    e2 = KnowledgeEntry(
        repository_id=repo.id, kind=KnowledgeKind.commit, source_ref="c2",
        title="omega", body="omega", embedding=[0.0, 1.0, 0.0],
    )
    db_session.add_all([e1, e2])
    db_session.flush()

    # Query embedding is close to e1's vector; keyword search matches neither.
    embedder = FakeEmbedder(query_vec=[0.9, 0.1, 0.0])
    hits = retrieve(db_session, repo.id, "zzz-nonmatching-term", embedder=embedder)
    assert hits and hits[0].source_ref == "c1"


def test_retrieve_falls_back_to_keyword_when_no_embedder(db_session):
    repo = _seed(db_session)
    # No embedder -> keyword FTS path (the Redis PR should surface).
    hits = retrieve(db_session, repo.id, "redis")
    assert hits and hits[0].source_ref == "182"


def test_embed_missing_stores_vectors(db_session):
    repo = _seed(db_session)  # seeds 2 entries without embeddings
    embedder = FakeEmbedder(query_vec=[0.0], batch_vecs=[[1.0, 0.0], [0.0, 1.0]])
    n = embed_missing(db_session, repo.id, embedder)
    assert n == 2
    vecs = [
        e.embedding
        for e in db_session.query(KnowledgeEntry).filter_by(repository_id=repo.id).all()
    ]
    assert all(v is not None for v in vecs)


async def test_answer_question_grounds_citations(db_session):
    repo = _seed(db_session)
    entries = retrieve(db_session, repo.id, "redis")
    ai = FakeAI({"answer": "Redis queues were added in PR #182.", "cited": [1]})
    result = await answer_question(ai, "why redis?", entries)
    assert "Redis" in result.answer
    assert result.cited_entries and result.cited_entries[0].source_ref == "182"
    assert result.provider == "gemini-1"


async def test_answer_question_ignores_out_of_range_citation(db_session):
    repo = _seed(db_session)
    entries = retrieve(db_session, repo.id, "redis")
    ai = FakeAI({"answer": "x", "cited": [99]})
    result = await answer_question(ai, "q", entries)
    assert result.cited_entries == []


async def test_answer_question_no_entries_short_circuits():
    ai = FakeAI({"answer": "should not be used", "cited": [1]})
    result = await answer_question(ai, "q", [])
    assert "don't have enough" in result.answer.lower()
    assert result.cited_entries == []
    assert ai.calls == []  # AI must not be consulted with no context


def test_ask_requires_auth(client):
    resp = client.post("/api/v1/repositories/1/ask", json={"question": "why?"})
    assert resp.status_code == 401


def test_ask_returns_cited_answer(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo = _seed(db_session, owner_id=user.id)
    monkeypatch.setattr(
        "app.api.routes.repositories.get_ai_service",
        lambda: FakeAI({"answer": "Redis queues were added in PR #182.", "cited": [1]}),
    )
    resp = api_client.post(f"/api/v1/repositories/{repo.id}/ask", json={"question": "why redis?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "Redis" in body["answer"]
    assert body["citations"] and body["citations"][0]["source_ref"] == "182"


def test_ask_503_without_ai(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo = _seed(db_session, owner_id=user.id)
    monkeypatch.setattr(
        "app.api.routes.repositories.get_ai_service",
        lambda: FakeAI({}, available=False),
    )
    resp = api_client.post(f"/api/v1/repositories/{repo.id}/ask", json={"question": "why?"})
    assert resp.status_code == 503
