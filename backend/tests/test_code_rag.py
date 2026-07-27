from __future__ import annotations

from app.models import CodeSymbol, GitHubInstallation, Repository, User
from app.services.qa import answer_question, retrieve_code
from app.services.symbols import embed_missing_symbols, symbol_text
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
    u = User(email=f"code{seq}@example.com", github_user_id=7700 + seq)
    db.add(u)
    db.flush()
    inst = GitHubInstallation(
        installation_id=8700 + seq, account_login="acme", account_type="User", owner_user_id=u.id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8701 + seq, full_name="acme/app",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def _sym(repo_id, name, path, **kw):
    base = {
        "kind": "function", "language": "python", "start_line": 10, "end_line": 20,
        "signature": f"def {name}(): ...",
    }
    base.update(kw)
    return CodeSymbol(repository_id=repo_id, name=name, path=path, **base)


def test_symbol_text_includes_name_path_signature():
    s = _sym(1, "charge_card", "src/pay.py")
    t = symbol_text(s)
    assert "charge_card" in t and "src/pay.py" in t and "def charge_card" in t


def test_embed_missing_symbols(db_session):
    repo = _repo(db_session, 0)
    db_session.add_all(
        [_sym(repo.id, "login", "src/auth.py"), _sym(repo.id, "logout", "src/auth.py")]
    )
    db_session.flush()
    embedder = FakeEmbedder([0.0], batch_vecs=[[1.0, 0.0], [0.0, 1.0]])
    assert embed_missing_symbols(db_session, repo.id, embedder) == 2
    vecs = [s.embedding for s in db_session.query(CodeSymbol).filter_by(repository_id=repo.id)]
    assert all(v is not None for v in vecs)
    # nothing left to embed on a second pass
    assert embed_missing_symbols(db_session, repo.id, FakeEmbedder([0.0])) == 0


def test_retrieve_code_keyword(db_session):
    repo = _repo(db_session, 1)
    db_session.add(_sym(repo.id, "rate_limit_middleware", "src/mw.py"))
    db_session.flush()
    hits = retrieve_code(db_session, repo.id, "how does rate limiting work")
    assert hits and hits[0].name == "rate_limit_middleware"


def test_retrieve_code_semantic(db_session):
    repo = _repo(db_session, 2)
    a = _sym(repo.id, "alpha", "src/a.py", embedding=[1.0, 0.0, 0.0])
    b = _sym(repo.id, "beta", "src/b.py", embedding=[0.0, 1.0, 0.0])
    db_session.add_all([a, b])
    db_session.flush()
    embedder = FakeEmbedder(query_vec=[0.95, 0.05, 0.0])
    hits = retrieve_code(db_session, repo.id, "zzz-nonmatching", embedder=embedder)
    assert hits and hits[0].name == "alpha"


async def test_answer_question_cites_code_with_github_url(db_session):
    repo = _repo(db_session, 3)
    sym = _sym(repo.id, "charge_card", "src/pay.py", start_line=12, end_line=30)
    db_session.add(sym)
    db_session.flush()
    ai = FakeAI({"answer": "Charging happens in charge_card.", "cited": [1]})
    result = await answer_question(
        ai, "where does charging happen?", [], code=[sym],
        repo_full_name="acme/app", default_branch="main",
    )
    assert result.cited_entries
    c = result.cited_entries[0]
    assert c.kind == "code"
    assert c.url == "https://github.com/acme/app/blob/main/src/pay.py#L12-L30"
    assert "src/pay.py" in c.source_ref


def test_ask_endpoint_blends_code(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    inst = GitHubInstallation(
        installation_id=8750, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db_session.add(inst)
    db_session.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8751, full_name="acme/ce", default_branch="main"
    )
    db_session.add(repo)
    db_session.flush()
    db_session.add(_sym(repo.id, "export_report", "src/export.py", start_line=5, end_line=9))
    db_session.flush()

    monkeypatch.setattr(
        "app.api.routes.repositories.get_ai_service",
        lambda: FakeAI({"answer": "Exports are built in export_report.", "cited": [1]}),
    )
    # Offline, deterministic embedder → semantic finds nothing embedded, keyword
    # path matches the symbol name. (Avoids a live embedding call in the test.)
    monkeypatch.setattr(
        "app.api.routes.repositories.get_embedding_service", lambda: FakeEmbedder([0.0])
    )
    resp = api_client.post(
        f"/api/v1/repositories/{repo.id}/ask", json={"question": "what does export_report do?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["citations"]
    cite = body["citations"][0]
    assert cite["kind"] == "code"
    assert cite["url"].startswith("https://github.com/acme/ce/blob/main/src/export.py")
