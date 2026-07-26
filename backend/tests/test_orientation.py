from __future__ import annotations

from app.models import (
    CodeSymbol,
    GitHubInstallation,
    KnowledgeEntry,
    KnowledgeKind,
    Repository,
    User,
)
from app.services import orientation as svc
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


def test_parse_guide_coerces_and_clamps():
    summary, content = svc.parse_guide(
        {
            "summary": "  A test repo.  ",
            "key_areas": [
                {"name": "API", "description": "routes", "paths": ["app/api"]},
                {"description": "no name -> dropped"},
                "not a dict",
            ],
            "getting_started": ["read README", "", "run tests"],
            "decisions": [{"title": "Use FastAPI", "detail": "async", "source": "PR #1"}],
            "conventions": ["ruff", 123],
        }
    )
    assert summary == "A test repo."
    assert [a["name"] for a in content["key_areas"]] == ["API"]
    assert content["key_areas"][0]["paths"] == ["app/api"]
    assert content["getting_started"] == ["read README", "run tests"]
    assert content["decisions"][0]["source"] == "PR #1"
    assert "ruff" in content["conventions"]


def test_parse_guide_handles_garbage():
    summary, content = svc.parse_guide({})
    assert summary == ""
    assert content == {
        "key_areas": [],
        "getting_started": [],
        "decisions": [],
        "conventions": [],
    }


def _seed(db, user_id: int, seq: int = 0) -> Repository:
    inst = GitHubInstallation(
        installation_id=9800 + seq, account_login="acme", account_type="User",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9801 + seq, full_name=f"acme/app{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def test_build_context_includes_structure_and_history(db_session):
    from tests.conftest import requires_db  # noqa: F401

    u = User(email="orient@example.com", github_user_id=9800)
    db_session.add(u)
    db_session.flush()
    repo = _seed(db_session, u.id)
    db_session.add_all(
        [
            CodeSymbol(
                repository_id=repo.id, path="src/pay.py", language="python",
                kind="function", name="charge",
            ),
            CodeSymbol(
                repository_id=repo.id, path="src/pay.py", language="python",
                kind="class", name="Wallet",
            ),
            KnowledgeEntry(
                repository_id=repo.id, kind=KnowledgeKind.pull_request, source_ref="12",
                title="Add Redis queue",
            ),
        ]
    )
    db_session.flush()

    context = svc.build_context(db_session, repo)
    assert "acme/app0" in context
    assert "python" in context
    assert "src" in context  # top-level module
    assert "Add Redis queue" in context
    assert "pull_request 12" in context


def test_generate_orientation_endpoint(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo = _seed(db_session, user.id, seq=1)
    db_session.add(
        CodeSymbol(
            repository_id=repo.id, path="src/app.py", language="python",
            kind="function", name="main",
        )
    )
    db_session.flush()

    fake = FakeAI(
        verdict={
            "summary": "A small payments service.",
            "key_areas": [{"name": "Payments", "description": "charging", "paths": ["src"]}],
            "getting_started": ["Start at src/app.py"],
            "decisions": [],
            "conventions": ["python"],
        }
    )
    monkeypatch.setattr("app.api.routes.repositories.get_ai_service", lambda: fake)

    resp = api_client.post(f"/api/v1/repositories/{repo.id}/orientation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == "A small payments service."
    assert data["key_areas"][0]["name"] == "Payments"

    # GET returns the stored guide
    got = api_client.get(f"/api/v1/repositories/{repo.id}/orientation")
    assert got.status_code == 200
    assert got.json()["summary"] == "A small payments service."


def test_orientation_404_when_absent(authed_client, db_session):
    api_client, user = authed_client
    repo = _seed(db_session, user.id, seq=2)
    db_session.flush()
    assert api_client.get(f"/api/v1/repositories/{repo.id}/orientation").status_code == 404


def test_orientation_requires_auth(client):
    assert client.get("/api/v1/repositories/1/orientation").status_code == 401
