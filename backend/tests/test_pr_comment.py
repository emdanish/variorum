from __future__ import annotations

from app.models import GitHubInstallation, Repository, User
from app.services import pr_comment as svc
from app.services.github.client import ChangedFile
from app.workers.pr_comment import run_pr_comment_job
from tests.conftest import requires_db

pytestmark = requires_db


class FakeGitHub:
    """Async stand-in for GitHubClient's comment API. Records posted bodies."""

    def __init__(self, existing: list[dict] | None = None):
        self.comments = existing or []
        self.created: list[str] = []
        self.updated: list[tuple[int, str]] = []

    async def list_issue_comments(self, _inst, _full, _number, **_kw):
        return self.comments

    async def create_issue_comment(self, _inst, _full, _number, body):
        self.created.append(body)
        return {"id": 111, "html_url": "https://gh/c/111"}

    async def update_issue_comment(self, _inst, _full, comment_id, body):
        self.updated.append((comment_id, body))
        return {"id": comment_id, "html_url": f"https://gh/c/{comment_id}"}


# --------------------------------------------------------------------------- #
# Rendering (pure)
# --------------------------------------------------------------------------- #

_BRIEFING = {
    "files": [
        {"path": "src/pay.py", "hotspot_score": 90, "hotspot_level": "critical",
         "has_tests": False, "module": "src", "primary_owner": "alice",
         "bus_factor": 1, "single_owner": True, "risk_findings": 2},
    ],
    "summary": {"files_analyzed": 1, "high_risk_files": 1, "single_owner_files": 1,
                "untested_files": 1, "top_file": "src/pay.py"},
}


def test_render_has_marker_and_content():
    body = svc.render_briefing_comment(
        _BRIEFING, repo_full_name="acme/app", default_branch="main",
        drift_open=2, risk_open=1,
    )
    assert svc.MARKER in body
    assert "Variorum PR briefing" in body
    assert "src/pay.py" in body
    assert "github.com/acme/app/blob/main/src/pay.py" in body
    assert "🔴 90" in body  # critical hotspot rendered
    assert "⚠️" in body  # single-owner flag
    assert "2" in body and "doc-drift" in body  # findings line
    assert "test-risk" in body


def test_render_empty_files():
    empty = {"files": [], "summary": {"files_analyzed": 0, "high_risk_files": 0,
             "single_owner_files": 0, "untested_files": 0, "top_file": None}}
    body = svc.render_briefing_comment(empty, repo_full_name="acme/app", default_branch="main")
    assert svc.MARKER in body
    assert "No indexed source files changed" in body


# --------------------------------------------------------------------------- #
# Sticky upsert
# --------------------------------------------------------------------------- #


async def test_upsert_creates_when_absent():
    gh = FakeGitHub(existing=[{"id": 1, "body": "unrelated human comment"}])
    result = await svc.upsert_pr_comment(gh, 5, "acme/app", 7, "body-" + svc.MARKER)
    assert result["action"] == "created"
    assert gh.created and not gh.updated


async def test_upsert_updates_existing_sticky():
    gh = FakeGitHub(existing=[{"id": 42, "body": "old " + svc.MARKER}])
    result = await svc.upsert_pr_comment(gh, 5, "acme/app", 7, "new " + svc.MARKER)
    assert result["action"] == "updated"
    assert gh.updated == [(42, "new " + svc.MARKER)]
    assert not gh.created


# --------------------------------------------------------------------------- #
# Worker (opt-in gating)
# --------------------------------------------------------------------------- #


def _repo(db, *, enabled: bool, seq: int = 0) -> Repository:
    u = User(email=f"prc{seq}@example.com", github_user_id=9900 + seq)
    db.add(u)
    db.flush()
    inst = GitHubInstallation(
        installation_id=9900 + seq, account_login="acme", account_type="User", owner_user_id=u.id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9901 + seq, full_name=f"acme/p{seq}",
        default_branch="main", pr_comments_enabled=enabled,
    )
    db.add(repo)
    db.flush()
    return repo


def test_worker_skips_when_disabled_and_required(db_session):
    repo = _repo(db_session, enabled=False, seq=0)
    gh = FakeGitHub()
    out = run_pr_comment_job(
        repo.id, 7, require_enabled=True, db=db_session, client=gh,
        pr_files=[ChangedFile(path="src/a.py", status="modified", patch=None,
                              additions=1, deletions=0)],
    )
    assert out is None
    assert not gh.created and not gh.updated


def test_worker_posts_when_enabled(db_session):
    repo = _repo(db_session, enabled=True, seq=1)
    gh = FakeGitHub()
    out = run_pr_comment_job(
        repo.id, 7, require_enabled=True, db=db_session, client=gh,
        pr_files=[ChangedFile(path="src/a.py", status="modified", patch=None,
                              additions=1, deletions=0)],
    )
    assert out is not None and out["action"] == "created"
    assert gh.created


def test_worker_manual_posts_even_when_disabled(db_session):
    repo = _repo(db_session, enabled=False, seq=2)
    gh = FakeGitHub()
    out = run_pr_comment_job(
        repo.id, 7, require_enabled=False, db=db_session, client=gh,
        pr_files=[ChangedFile(path="src/a.py", status="modified", patch=None,
                              additions=1, deletions=0)],
    )
    assert out is not None and out["action"] == "created"


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


def test_toggle_pr_comments_endpoint(authed_client, db_session):
    api_client, user = authed_client
    inst = GitHubInstallation(
        installation_id=9950, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db_session.add(inst)
    db_session.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9951, full_name="acme/tog", default_branch="main"
    )
    db_session.add(repo)
    db_session.flush()

    resp = api_client.put(f"/api/v1/repositories/{repo.id}/pr-comments", json={"enabled": True})
    assert resp.status_code == 200 and resp.json() == {"enabled": True}
    db_session.refresh(repo)
    assert repo.pr_comments_enabled is True


def test_manual_post_endpoint(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    inst = GitHubInstallation(
        installation_id=9960, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db_session.add(inst)
    db_session.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9961, full_name="acme/man", default_branch="main"
    )
    db_session.add(repo)
    db_session.flush()

    monkeypatch.setattr(
        "app.api.routes.repositories.run_pr_comment_job",
        lambda *a, **k: {"action": "created", "url": "https://gh/c/1"},
    )
    resp = api_client.post(f"/api/v1/repositories/{repo.id}/pr-comment/7")
    assert resp.status_code == 200
    assert resp.json() == {"action": "created", "url": "https://gh/c/1"}


def test_pr_comment_endpoints_require_auth(client):
    put = client.put("/api/v1/repositories/1/pr-comments", json={"enabled": True})
    assert put.status_code == 401
    assert client.post("/api/v1/repositories/1/pr-comment/1").status_code == 401
