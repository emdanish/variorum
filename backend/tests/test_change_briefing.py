from __future__ import annotations

from app.models import (
    CodeSymbol,
    DecisionEntry,
    DocCodeLink,
    Document,
    FileChange,
    GitHubInstallation,
    KnowledgeEntry,
    KnowledgeKind,
    Repository,
    User,
)
from app.services import change_briefing as svc
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


def _seed(db, owner_id=None) -> Repository:
    if owner_id is None:
        u = User(email="cb@example.com", github_user_id=7300)
        db.add(u)
        db.flush()
        owner_id = u.id
    inst = GitHubInstallation(
        installation_id=8300, account_login="acme", account_type="User", owner_user_id=owner_id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8301, full_name="acme/app", default_branch="main"
    )
    db.add(repo)
    db.flush()

    sym = CodeSymbol(
        repository_id=repo.id, path="src/pay.py", language="python", kind="function",
        name="charge_card", start_line=10, end_line=25, signature="def charge_card(...): ...",
    )
    db.add(sym)
    # churn so hotspots + ownership have data (alice = sole owner of src/)
    db.add_all(
        [
            FileChange(repository_id=repo.id, commit_sha=f"c{i}", path="src/pay.py",
                       author="alice", additions=10, deletions=2, is_fix=(i == 0))
            for i in range(3)
        ]
    )
    db.add(
        DecisionEntry(
            repository_id=repo.id, title="Charge cards synchronously",
            summary="Payments charge inline for simplicity; async was rejected.", sources=[],
        )
    )
    db.add(
        KnowledgeEntry(
            repository_id=repo.id, kind=KnowledgeKind.pull_request, source_ref="42",
            title="Add card charging", body="Introduce charge_card for payments.",
            url="https://gh/pr/42",
        )
    )
    doc = Document(repository_id=repo.id, path="docs/payments.md", title="Payments guide")
    db.add(doc)
    db.flush()
    db.add(DocCodeLink(document_id=doc.id, path="src/pay.py", confidence=0.9))
    db.flush()
    return repo


_Q = "why do we charge cards in payments"


def test_briefing_locates_code_with_url(db_session):
    repo = _seed(db_session)
    b = svc.build_change_briefing(
        db_session, repo.id, _Q, repo_full_name="acme/app", default_branch="main"
    )
    assert b["locations"]
    loc = b["locations"][0]
    assert loc["path"] == "src/pay.py" and loc["name"] == "charge_card"
    assert loc["url"] == "https://github.com/acme/app/blob/main/src/pay.py#L10"
    assert loc["module"] == "src"


def test_briefing_names_owner_and_flags_bus_factor(db_session):
    repo = _seed(db_session)
    b = svc.build_change_briefing(db_session, repo.id, _Q, repo_full_name="acme/app")
    experts = {e["module"]: e for e in b["experts"]}
    assert "src" in experts
    assert experts["src"]["primary_owner"] == "alice"
    assert experts["src"]["single_owner"] is True  # sole owner → who to loop in


def test_briefing_surfaces_why_and_docs_and_test_gaps(db_session):
    repo = _seed(db_session)
    b = svc.build_change_briefing(db_session, repo.id, _Q, repo_full_name="acme/app")
    assert any("Charge cards" in d["title"] for d in b["decisions"])
    assert any(h["source_ref"] == "42" for h in b["history"])
    assert any(d["path"] == "docs/payments.md" for d in b["docs_to_update"])
    # src/pay.py has no matching test file → flagged as a test gap
    assert "src/pay.py" in b["test_gaps"]


async def test_summarize_best_effort(db_session):
    repo = _seed(db_session)
    b = svc.build_change_briefing(db_session, repo.id, _Q, repo_full_name="acme/app")
    summary, provider = await svc.summarize(FakeAI({}, text="Touch src/pay.py carefully."), b)
    assert summary == "Touch src/pay.py carefully." and provider == "gemini-1"
    # unavailable AI → no summary, briefing still stands
    none_summary, none_provider = await svc.summarize(FakeAI({}, available=False), b)
    assert none_summary is None and none_provider is None


def test_change_briefing_endpoint(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo = _seed(db_session, owner_id=user.id)
    monkeypatch.setattr(
        "app.api.routes.repositories.get_ai_service",
        lambda: FakeAI({}, text="Before you start: loop in alice; add tests for src/pay.py."),
    )
    # Offline embedder so retrieval is deterministic (keyword path).
    monkeypatch.setattr(
        "app.api.routes.repositories.get_embedding_service",
        lambda: type("E", (), {"available": False})(),
    )
    resp = api_client.post(
        f"/api/v1/repositories/{repo.id}/change-briefing", json={"query": _Q}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["locations"] and body["locations"][0]["name"] == "charge_card"
    assert body["summary"].startswith("Before you start")
    # too-short query rejected
    assert (
        api_client.post(
            f"/api/v1/repositories/{repo.id}/change-briefing", json={"query": "x"}
        ).status_code
        == 422
    )


def test_change_briefing_requires_auth(client):
    resp = client.post("/api/v1/repositories/1/change-briefing", json={"query": "add a field"})
    assert resp.status_code == 401
