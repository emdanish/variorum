from __future__ import annotations

from datetime import UTC, datetime

from app.models import (
    AnalysisJob,
    DriftFinding,
    DriftSeverity,
    FileChange,
    FindingStatus,
    GitHubInstallation,
    JobStatus,
    JobTrigger,
    JobType,
    KnowledgeEntry,
    KnowledgeKind,
    Repository,
    RiskFinding,
    User,
)
from app.services import experts as experts_svc
from app.services import portfolio as portfolio_svc
from tests.conftest import requires_db

pytestmark = requires_db


def _repo(db, user_id, seq, name):
    inst = GitHubInstallation(
        installation_id=9100 + seq, account_login="acme", account_type="Organization",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9101 + seq, full_name=name,
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def _fc(db, repo_id, sha, path, author, adds=10, dels=2):
    db.add(
        FileChange(
            repository_id=repo_id, commit_sha=sha, path=path, author=author,
            additions=adds, deletions=dels, is_fix=False,
            occurred_at=datetime(2026, 7, 26, tzinfo=UTC),
        )
    )


def test_build_portfolio_ranks_repos(db_session):
    u = User(email="pf@example.com", github_user_id=9100)
    db_session.add(u)
    db_session.flush()
    _repo(db_session, u.id, 0, "acme/healthy")
    r2 = _repo(db_session, u.id, 1, "acme/risky")
    # risky repo: a source symbol + open drift + single-owner churn
    job = AnalysisJob(repository_id=r2.id, type=JobType.pr_analysis, status=JobStatus.succeeded,
                      trigger=JobTrigger.manual)
    db_session.add(job)
    db_session.flush()
    db_session.add_all(
        [
            DriftFinding(analysis_job_id=job.id, severity=DriftSeverity.high, summary="d",
                         evidence={}, status=FindingStatus.detected),
            RiskFinding(analysis_job_id=job.id, path="src/pay.py", risk_level=DriftSeverity.high,
                        summary="r", evidence={}),
        ]
    )
    _fc(db_session, r2.id, "c1", "src/pay.py", "solo", 100, 0)
    db_session.flush()

    pf = portfolio_svc.build_portfolio(db_session, u.id)
    names = [r["full_name"] for r in pf["repos"]]
    assert set(names) == {"acme/healthy", "acme/risky"}
    # worst health first
    assert pf["repos"][0]["health_score"] <= pf["repos"][1]["health_score"]
    risky = next(r for r in pf["repos"] if r["full_name"] == "acme/risky")
    assert risky["drift_open"] == 1
    assert risky["risk_high"] == 1
    assert pf["summary"]["repo_count"] == 2


def test_portfolio_endpoint(authed_client, db_session):
    api_client, user = authed_client
    _repo(db_session, user.id, 2, "acme/p")
    db_session.flush()
    resp = api_client.get("/api/v1/portfolio")
    assert resp.status_code == 200
    assert resp.json()["summary"]["repo_count"] >= 1


def test_portfolio_requires_auth(client):
    assert client.get("/api/v1/portfolio").status_code == 401


def test_build_experts_and_filter(db_session):
    u = User(email="ex@example.com", github_user_id=9110)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, 3, "acme/svc")
    _fc(db_session, repo.id, "c1", "billing/charge.py", "alice", 80, 10)
    _fc(db_session, repo.id, "c2", "billing/refund.py", "alice", 30, 5)
    _fc(db_session, repo.id, "c3", "frontend/app.tsx", "bob", 20, 2)
    db_session.add(
        KnowledgeEntry(repository_id=repo.id, kind=KnowledgeKind.pull_request,
                       source_ref="1", title="pr", author="alice")
    )
    db_session.flush()

    directory = experts_svc.build_experts(db_session, u.id)
    by_author = {e["author"]: e for e in directory["experts"]}
    assert by_author["alice"]["churn"] > by_author["bob"]["churn"]
    assert "acme/svc" in by_author["alice"]["repos"]
    assert by_author["alice"]["top_modules"][0]["module"] == "billing"
    assert "Python" in by_author["alice"]["languages"]
    assert by_author["alice"]["prs_authored"] == 1
    assert "TypeScript" in by_author["bob"]["languages"]
    # alice is the sole author of the billing module -> bus-factor risk
    assert any(o["module"] == "billing" for o in by_author["alice"]["owns"])

    # filter by area
    filtered = experts_svc.build_experts(db_session, u.id, q="billing")
    assert [e["author"] for e in filtered["experts"]] == ["alice"]


def test_experts_endpoint(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, user.id, 4, "acme/e")
    _fc(db_session, repo.id, "c1", "src/a.py", "alice")
    db_session.flush()
    resp = api_client.get("/api/v1/experts")
    assert resp.status_code == 200
    assert any(e["author"] == "alice" for e in resp.json()["experts"])


def test_experts_requires_auth(client):
    assert client.get("/api/v1/experts").status_code == 401
