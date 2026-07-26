from __future__ import annotations

from datetime import UTC, datetime

from app.models import (
    CodeSymbol,
    DocCodeLink,
    Document,
    GitHubInstallation,
    Repository,
    User,
)
from app.services import metrics as svc
from tests.conftest import requires_db

pytestmark = requires_db


def test_is_fix_message():
    assert svc.is_fix_message("Fix null pointer in charge()")
    assert svc.is_fix_message("hotfix: revert bad deploy")
    assert not svc.is_fix_message("Add new billing feature")
    assert not svc.is_fix_message(None)


def test_bus_factor_pure():
    assert svc._bus_factor([]) == 0
    assert svc._bus_factor([100]) == 1
    assert svc._bus_factor([90, 5, 5]) == 1  # one author > 50%
    assert svc._bus_factor([40, 35, 25]) == 2  # need two to reach 50%


def test_level_pure():
    assert svc._level(80) == "critical"
    assert svc._level(50) == "high"
    assert svc._level(30) == "medium"
    assert svc._level(10) == "low"


def _repo(db, user_id: int, seq: int = 0) -> Repository:
    inst = GitHubInstallation(
        installation_id=9900 + seq, account_login="acme", account_type="User",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9901 + seq, full_name=f"acme/m{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def _change(db, repo_id, sha, path, author, adds, dels, is_fix=False):
    db.add(
        svc.FileChange(
            repository_id=repo_id, commit_sha=sha, path=path, author=author,
            additions=adds, deletions=dels, is_fix=is_fix,
            occurred_at=datetime(2026, 7, 26, tzinfo=UTC),
        )
    )


def test_store_file_changes_idempotent(db_session):
    u = User(email="m@example.com", github_user_id=9900)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id)
    recs = [
        svc.FileChangeRecord("sha1", "src/a.py", "alice", 10, 2, False, None),
        svc.FileChangeRecord("sha1", "src/a.py", "alice", 10, 2, False, None),  # dup
        svc.FileChangeRecord("sha2", "src/a.py", "bob", 3, 1, True, None),
    ]
    assert svc.store_file_changes(db_session, repo.id, recs) == 2
    assert svc.store_file_changes(db_session, repo.id, recs) == 0  # already stored
    assert svc.has_file_changes(db_session, repo.id) is True


def test_compute_hotspots(db_session):
    u = User(email="h@example.com", github_user_id=9910)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, seq=1)
    # hot file: many changes, big churn, fixes, no tests
    for i in range(5):
        _change(db_session, repo.id, f"c{i}", "src/pay.py", f"dev{i%2}", 50, 20, is_fix=(i < 3))
    # calm file: one small change, has a test
    _change(db_session, repo.id, "d0", "src/util.py", "alice", 2, 0)
    db_session.add_all(
        [
            CodeSymbol(repository_id=repo.id, path="src/util.py", language="python",
                       kind="function", name="u"),
            CodeSymbol(repository_id=repo.id, path="tests/test_util.py", language="python",
                       kind="function", name="test_u"),
        ]
    )
    db_session.flush()

    hotspots = svc.compute_hotspots(db_session, repo.id)
    assert hotspots[0]["path"] == "src/pay.py"
    assert hotspots[0]["score"] > 0
    assert hotspots[0]["fixes"] == 3
    assert hotspots[0]["has_tests"] is False
    util = next(h for h in hotspots if h["path"] == "src/util.py")
    assert util["has_tests"] is True


def test_compute_ownership_bus_factor(db_session):
    u = User(email="o@example.com", github_user_id=9920)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, seq=2)
    # auth module: one dominant author -> single owner
    _change(db_session, repo.id, "a1", "auth/login.py", "solo", 100, 0)
    _change(db_session, repo.id, "a2", "auth/login.py", "solo", 80, 0)
    _change(db_session, repo.id, "a3", "auth/login.py", "other", 5, 0)
    # api module: balanced
    _change(db_session, repo.id, "b1", "api/routes.py", "x", 40, 0)
    _change(db_session, repo.id, "b2", "api/routes.py", "y", 35, 0)
    db_session.flush()

    report = svc.compute_ownership(db_session, repo.id)
    by_mod = {m["module"]: m for m in report["modules"]}
    assert by_mod["auth"]["single_owner"] is True
    assert by_mod["auth"]["primary_owner"] == "solo"
    assert by_mod["api"]["single_owner"] is False
    assert report["single_owner_modules"] == 1


def test_compute_doc_coverage(db_session):
    u = User(email="d@example.com", github_user_id=9930)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, seq=3)
    s1 = CodeSymbol(repository_id=repo.id, path="src/a.py", language="python",
                    kind="function", name="a")
    s2 = CodeSymbol(repository_id=repo.id, path="src/b.py", language="python",
                    kind="function", name="b")
    doc = Document(repository_id=repo.id, path="README.md", title="R")
    db_session.add_all([s1, s2, doc])
    db_session.flush()
    db_session.add(DocCodeLink(document_id=doc.id, symbol_id=s1.id, confidence=0.9))
    db_session.flush()

    cov = svc.compute_doc_coverage(db_session, repo.id)
    assert cov["total"] == 2
    assert cov["documented"] == 1
    assert cov["overall_pct"] == 50.0


def test_compute_health_composite(db_session):
    u = User(email="hc@example.com", github_user_id=9940)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, seq=4)
    db_session.add(
        CodeSymbol(repository_id=repo.id, path="src/a.py", language="python",
                   kind="function", name="a")
    )
    _change(db_session, repo.id, "a1", "src/a.py", "solo", 100, 0)
    db_session.flush()

    health = svc.compute_health(db_session, repo.id)
    assert 0 <= health["score"] <= 100
    assert health["level"] in {"critical", "high", "medium", "low"}
    assert "coverage" in health["subscores"]  # has source files


def test_metrics_endpoints(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, user.id, seq=5)
    _change(db_session, repo.id, "c1", "src/pay.py", "alice", 30, 10, is_fix=True)
    db_session.add(
        CodeSymbol(repository_id=repo.id, path="src/pay.py", language="python",
                   kind="function", name="charge")
    )
    db_session.flush()

    assert api_client.get(f"/api/v1/repositories/{repo.id}/hotspots").status_code == 200
    assert api_client.get(f"/api/v1/repositories/{repo.id}/ownership").status_code == 200
    assert api_client.get(f"/api/v1/repositories/{repo.id}/doc-coverage").status_code == 200
    health = api_client.get(f"/api/v1/repositories/{repo.id}/health")
    assert health.status_code == 200
    assert "score" in health.json()


def test_metrics_endpoints_require_auth(client):
    for path in ("hotspots", "ownership", "doc-coverage", "health"):
        assert client.get(f"/api/v1/repositories/1/{path}").status_code == 401
