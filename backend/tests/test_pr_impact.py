from __future__ import annotations

from datetime import UTC, datetime

from app.models import (
    AnalysisJob,
    DriftSeverity,
    FileChange,
    GitHubInstallation,
    JobStatus,
    JobTrigger,
    JobType,
    Repository,
    RiskFinding,
    User,
)
from app.services import pr_impact as svc
from app.services.github.client import ChangedFile
from tests.conftest import requires_db

pytestmark = requires_db


def _seed(db, user_id, seq=0):
    inst = GitHubInstallation(
        installation_id=9500 + seq, account_login="acme", account_type="User",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9501 + seq, full_name=f"acme/pr{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    job = AnalysisJob(
        repository_id=repo.id, type=JobType.pr_analysis, status=JobStatus.succeeded,
        trigger=JobTrigger.manual,
    )
    db.add(job)
    db.flush()
    return repo, job


def _fc(db, repo_id, sha, path, author, adds, dels, is_fix=False):
    db.add(
        FileChange(
            repository_id=repo_id, commit_sha=sha, path=path, author=author,
            additions=adds, deletions=dels, is_fix=is_fix,
            occurred_at=datetime(2026, 7, 26, tzinfo=UTC),
        )
    )


def test_build_briefing_composes_signals(db_session):
    u = User(email="pri@example.com", github_user_id=9500)
    db_session.add(u)
    db_session.flush()
    repo, job = _seed(db_session, u.id)
    for i in range(4):
        _fc(db_session, repo.id, f"c{i}", "src/pay.py", "solo", 50, 10, is_fix=(i < 2))
    db_session.add(
        RiskFinding(
            analysis_job_id=job.id, path="src/pay.py", risk_level=DriftSeverity.high,
            summary="risky", evidence={},
        )
    )
    db_session.flush()

    briefing = svc.build_briefing(db_session, repo.id, ["src/pay.py", "README.md", "src/new.py"])
    # README.md is not a source path -> excluded
    paths = [f["path"] for f in briefing["files"]]
    assert "README.md" not in paths
    assert "src/pay.py" in paths
    pay = next(f for f in briefing["files"] if f["path"] == "src/pay.py")
    assert pay["hotspot_score"] is not None
    assert pay["single_owner"] is True
    assert pay["primary_owner"] == "solo"
    assert pay["risk_findings"] == 1
    # a changed source file with no churn history still appears (no hotspot)
    new = next(f for f in briefing["files"] if f["path"] == "src/new.py")
    assert new["hotspot_score"] is None
    assert briefing["summary"]["files_analyzed"] == 2


def test_pr_briefing_endpoint(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo, _ = _seed(db_session, user.id, seq=1)
    _fc(db_session, repo.id, "c1", "src/app.py", "alice", 20, 5)
    db_session.flush()

    async def fake_files(self, installation_id, full_name, number):
        return [
            ChangedFile(path="src/app.py", status="modified", patch=None, additions=3, deletions=1)
        ]

    monkeypatch.setattr(
        "app.api.routes.repositories.GitHubClient.list_pull_request_files", fake_files
    )
    monkeypatch.setattr("app.api.routes.repositories.get_github_auth", lambda: object())

    resp = api_client.get(f"/api/v1/repositories/{repo.id}/pr-briefing/7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pr_number"] == 7
    assert data["files"][0]["path"] == "src/app.py"


def test_pr_briefing_rejects_bad_number(authed_client, db_session):
    api_client, user = authed_client
    repo, _ = _seed(db_session, user.id, seq=2)
    db_session.flush()
    assert api_client.get(f"/api/v1/repositories/{repo.id}/pr-briefing/0").status_code == 400


def test_pr_briefing_requires_auth(client):
    assert client.get("/api/v1/repositories/1/pr-briefing/1").status_code == 401
