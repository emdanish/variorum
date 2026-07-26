from __future__ import annotations

from app.models import (
    AnalysisJob,
    DriftFinding,
    DriftSeverity,
    FindingStatus,
    GitHubInstallation,
    JobStatus,
    JobTrigger,
    JobType,
    Repository,
    RiskFinding,
    User,
)
from tests.conftest import requires_db

pytestmark = requires_db


def _seed_job(db, user_id: int, seq: int = 0) -> AnalysisJob:
    inst = GitHubInstallation(
        installation_id=9400 + seq, account_login="acme", account_type="User",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9401 + seq, full_name=f"acme/triage{seq}",
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
    return job


def _drift(db, job) -> DriftFinding:
    f = DriftFinding(
        analysis_job_id=job.id, severity=DriftSeverity.medium, summary="doc drift",
        evidence={}, status=FindingStatus.detected,
    )
    db.add(f)
    db.flush()
    return f


def _risk(db, job) -> RiskFinding:
    f = RiskFinding(
        analysis_job_id=job.id, path="src/payment.py", risk_level=DriftSeverity.high,
        summary="untested change", evidence={}, status="open",
    )
    db.add(f)
    db.flush()
    return f


def test_dismiss_and_restore_drift_finding(authed_client, db_session):
    api_client, user = authed_client
    job = _seed_job(db_session, user.id)
    finding = _drift(db_session, job)

    resp = api_client.post(f"/api/v1/findings/{finding.id}/dismiss")
    assert resp.status_code == 200
    assert resp.json()["status"] == FindingStatus.dismissed.value

    resp = api_client.post(f"/api/v1/findings/{finding.id}/restore")
    assert resp.status_code == 200
    assert resp.json()["status"] == FindingStatus.detected.value


def test_dismiss_does_not_touch_pr_opened_finding(authed_client, db_session):
    api_client, user = authed_client
    job = _seed_job(db_session, user.id, seq=1)
    finding = _drift(db_session, job)
    finding.status = FindingStatus.pr_opened
    db_session.flush()

    resp = api_client.post(f"/api/v1/findings/{finding.id}/dismiss")
    assert resp.status_code == 200
    assert resp.json()["status"] == FindingStatus.pr_opened.value


def test_dismiss_and_restore_risk_finding(authed_client, db_session):
    api_client, user = authed_client
    job = _seed_job(db_session, user.id, seq=2)
    finding = _risk(db_session, job)

    resp = api_client.post(f"/api/v1/risk-findings/{finding.id}/dismiss")
    assert resp.status_code == 200
    assert resp.json()["status"] == "dismissed"

    resp = api_client.post(f"/api/v1/risk-findings/{finding.id}/restore")
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"


def test_triage_scoped_to_owner(authed_client, db_session):
    api_client, _ = authed_client
    other = User(email="stranger@example.com", github_user_id=9999)
    db_session.add(other)
    db_session.flush()
    job = _seed_job(db_session, other.id, seq=3)
    drift = _drift(db_session, job)
    risk = _risk(db_session, job)

    assert api_client.post(f"/api/v1/findings/{drift.id}/dismiss").status_code == 404
    assert api_client.post(f"/api/v1/risk-findings/{risk.id}/dismiss").status_code == 404


def test_triage_requires_auth(client):
    assert client.post("/api/v1/findings/1/dismiss").status_code == 401
    assert client.post("/api/v1/risk-findings/1/dismiss").status_code == 401
