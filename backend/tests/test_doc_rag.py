from __future__ import annotations

from app.models import Document, GitHubInstallation, Repository, User
from app.services.documents import document_text, embed_missing_documents
from app.services.indexer.pipeline import reindex_repository
from app.services.qa import answer_question, retrieve_docs
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


class FakeEmbedder:
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


def _repo(db, seq=0) -> Repository:
    u = User(email=f"doc{seq}@example.com", github_user_id=7600 + seq)
    db.add(u)
    db.flush()
    inst = GitHubInstallation(
        installation_id=8600 + seq, account_login="acme", account_type="User", owner_user_id=u.id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8601 + seq, full_name="acme/app",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def _doc(repo_id, path, title, body, **kw):
    return Document(repository_id=repo_id, path=path, title=title, body=body, **kw)


def test_document_text_combines_title_and_body():
    d = Document(repository_id=1, path="docs/a.md", title="Auth guide", body="How login works.")
    t = document_text(d)
    assert "Auth guide" in t and "How login works." in t


def test_pipeline_stores_body(db_session, sample_repo):
    repo = _repo(db_session, 0)
    reindex_repository(db_session, repo, sample_repo)
    readme = db_session.query(Document).filter_by(repository_id=repo.id, path="README.md").one()
    assert readme.body and "Sample Project" in readme.body


def test_embed_missing_documents(db_session):
    repo = _repo(db_session, 1)
    db_session.add_all(
        [
            _doc(repo.id, "docs/a.md", "A", "alpha body"),
            _doc(repo.id, "docs/b.md", "B", "beta body"),
            _doc(repo.id, "docs/empty.md", "E", None),  # no body → skipped
        ]
    )
    db_session.flush()
    n = embed_missing_documents(
        db_session, repo.id, FakeEmbedder([0.0], batch_vecs=[[1.0, 0.0], [0.0, 1.0]])
    )
    assert n == 2  # only the two with a body


def test_retrieve_docs_keyword(db_session):
    repo = _repo(db_session, 2)
    db_session.add(
        _doc(repo.id, "docs/auth.md", "Authentication", "We use JWT tokens for stateless auth.")
    )
    db_session.flush()
    hits = retrieve_docs(db_session, repo.id, "how does jwt authentication work")
    assert hits and hits[0].path == "docs/auth.md"


def test_retrieve_docs_semantic(db_session):
    repo = _repo(db_session, 3)
    a = _doc(repo.id, "docs/a.md", "A", "alpha", embedding=[1.0, 0.0, 0.0])
    b = _doc(repo.id, "docs/b.md", "B", "beta", embedding=[0.0, 1.0, 0.0])
    db_session.add_all([a, b])
    db_session.flush()
    hits = retrieve_docs(
        db_session, repo.id, "zzz-nonmatching", embedder=FakeEmbedder([0.95, 0.05, 0.0])
    )
    assert hits and hits[0].path == "docs/a.md"


async def test_answer_question_cites_document_with_url(db_session):
    repo = _repo(db_session, 4)
    d = _doc(repo.id, "docs/auth.md", "Auth", "JWT tokens.")
    db_session.add(d)
    db_session.flush()
    ai = FakeAI({"answer": "Auth uses JWT.", "cited": [1]})
    result = await answer_question(
        ai, "how does auth work?", [], documents=[d],
        repo_full_name="acme/app", default_branch="main",
    )
    assert result.cited_entries
    c = result.cited_entries[0]
    assert c.kind == "document"
    assert c.url == "https://github.com/acme/app/blob/main/docs/auth.md"
    assert c.source_ref == "docs/auth.md"


def test_ask_endpoint_blends_docs(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    inst = GitHubInstallation(
        installation_id=8690, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db_session.add(inst)
    db_session.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8691, full_name="acme/de", default_branch="main"
    )
    db_session.add(repo)
    db_session.flush()
    db_session.add(
        _doc(repo.id, "docs/deploy.md", "Deploy", "Deployment uses the production checklist.")
    )
    db_session.flush()

    monkeypatch.setattr(
        "app.api.routes.repositories.get_ai_service",
        lambda: FakeAI({"answer": "See the deploy guide.", "cited": [1]}),
    )
    monkeypatch.setattr(
        "app.api.routes.repositories.get_embedding_service", lambda: FakeEmbedder([0.0])
    )
    resp = api_client.post(
        f"/api/v1/repositories/{repo.id}/ask", json={"question": "how does deployment work?"}
    )
    assert resp.status_code == 200
    cites = resp.json()["citations"]
    assert cites and cites[0]["kind"] == "document"
    assert cites[0]["url"].endswith("/blob/main/docs/deploy.md")
