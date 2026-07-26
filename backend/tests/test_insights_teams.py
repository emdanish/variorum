from __future__ import annotations

from datetime import UTC, datetime

from app.models import (
    AnalysisJob,
    DriftFinding,
    DriftSeverity,
    FindingStatus,
    GitHubInstallation,
    JobStatus,
    JobTrigger,
    JobType,
    KnowledgeEntry,
    KnowledgeKind,
    Repository,
    RiskFinding,
)
from app.services import insights as insights_svc
from tests.conftest import requires_db

pytestmark = requires_db


def test_doc_health_score_pure():
    assert insights_svc.doc_health_score({}) == 100
    assert insights_svc.doc_health_score({"high": 2}) == 70  # 100 - 2*15
    assert insights_svc.doc_health_score({"high": 10}) == 0  # floored


def test_activity_series_pure():
    now = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)
    series = insights_svc.activity_series(
        [datetime(2026, 7, 26, tzinfo=UTC)],
        [datetime(2026, 7, 25, tzinfo=UTC)],
        days=3,
        now=now,
    )
    assert len(series) == 3
    assert series[-1] == {"date": "2026-07-26", "drift": 1, "risk": 0}
    assert series[-2] == {"date": "2026-07-25", "drift": 0, "risk": 1}


def _seed(db, user_id: int, seq: int = 0) -> tuple[GitHubInstallation, Repository, AnalysisJob]:
    inst = GitHubInstallation(
        installation_id=9600 + seq, account_login=f"acme{seq}", account_type="Organization",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9601 + seq, full_name=f"acme/app{seq}",
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
    return inst, repo, job


def test_repository_insights_endpoint(authed_client, db_session):
    api_client, user = authed_client
    _, repo, job = _seed(db_session, user.id)
    db_session.add_all(
        [
            DriftFinding(
                analysis_job_id=job.id, severity=DriftSeverity.high, summary="d1",
                evidence={}, status=FindingStatus.detected,
            ),
            RiskFinding(
                analysis_job_id=job.id, path="src/pay.py", risk_level=DriftSeverity.high,
                summary="r1", evidence={"has_tests": False},
            ),
            RiskFinding(
                analysis_job_id=job.id, path="src/pay.py", risk_level=DriftSeverity.medium,
                summary="r2", evidence={"has_tests": True},
            ),
            KnowledgeEntry(
                repository_id=repo.id, kind=KnowledgeKind.commit, source_ref="abc", title="c",
            ),
        ]
    )
    db_session.flush()

    resp = api_client.get(f"/api/v1/repositories/{repo.id}/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert data["drift_total"] == 1
    assert data["drift_open"] == 1
    assert data["doc_health"] == 85  # 100 - 1 high (15)
    assert data["risk_total"] == 2
    assert data["high_risk"] == 1
    assert data["tested_ratio"] == 0.5
    assert data["knowledge_total"] == 1
    assert data["top_risk_paths"][0]["path"] == "src/pay.py"
    assert data["top_risk_paths"][0]["risk_level"] == "high"
    assert len(data["activity"]) == 14


def test_repository_insights_requires_auth(client):
    assert client.get("/api/v1/repositories/1/insights").status_code == 401


def test_teams_endpoint(authed_client, db_session):
    api_client, user = authed_client
    inst, repo, job = _seed(db_session, user.id, seq=1)
    repo.indexing_status = repo.indexing_status  # keep default (pending)
    db_session.add_all(
        [
            RiskFinding(
                analysis_job_id=job.id, path="a.py", risk_level=DriftSeverity.high,
                summary="r", evidence={},
            ),
            KnowledgeEntry(
                repository_id=repo.id, kind=KnowledgeKind.pull_request, source_ref="1", title="p",
            ),
        ]
    )
    db_session.flush()

    resp = api_client.get("/api/v1/teams")
    assert resp.status_code == 200
    teams = resp.json()
    mine = [t for t in teams if t["account_login"] == "acme1"]
    assert len(mine) == 1
    team = mine[0]
    assert team["repo_count"] == 1
    assert team["risk_total"] == 1
    assert team["high_risk"] == 1
    assert team["knowledge_total"] == 1
    assert team["account_type"] == "Organization"


def test_teams_requires_auth(client):
    assert client.get("/api/v1/teams").status_code == 401
