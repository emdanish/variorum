from __future__ import annotations

from sqlalchemy import select

from app.models import (
    AnalysisJob,
    CodeSymbol,
    DriftSeverity,
    GitHubInstallation,
    JobStatus,
    Repository,
    RiskFinding,
    User,
)
from app.services.analysis.risk import compute_signals, is_source_path, is_test_path
from app.services.github.client import ChangedFile
from app.workers.risk_analysis import run_risk_analysis_job
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


def test_path_classification():
    assert is_test_path("tests/test_payment.py")
    assert is_test_path("src/foo.test.ts")
    assert is_test_path("app/__tests__/x.spec.ts")
    assert not is_test_path("src/payment.py")
    assert is_source_path("src/payment.py")
    assert not is_source_path("tests/test_payment.py")  # test file
    assert not is_source_path("README.md")  # not code


def _seed(
    db, *, owner_id: int | None = None, with_test_file: bool = False, seq: int = 0
) -> Repository:
    uid = owner_id
    if uid is None:
        u = User(email=f"risk{seq}@example.com", github_user_id=7300 + seq)
        db.add(u)
        db.flush()
        uid = u.id
    inst = GitHubInstallation(
        installation_id=8700 + seq, account_login="acme", account_type="User", owner_user_id=uid
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id,
        github_repo_id=8701 + seq,
        full_name=f"acme/app{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    db.add(
        CodeSymbol(
            repository_id=repo.id, path="src/payment.py", language="python",
            kind="function", name="charge",
        )
    )
    if with_test_file:
        db.add(
            CodeSymbol(
                repository_id=repo.id, path="tests/test_payment.py", language="python",
                kind="function", name="test_charge",
            )
        )
    db.flush()
    return repo


_CHANGED = ChangedFile(
    path="src/payment.py", status="modified", patch="@@\n+def charge(): ...", additions=20,
    deletions=3,
)


def test_compute_signals_detects_missing_and_present_tests(db_session):
    repo = _seed(db_session, with_test_file=False)
    sig = compute_signals(db_session, repo.id, _CHANGED)
    assert sig.churn == 23
    assert sig.symbol_count == 1
    assert sig.has_tests is False

    repo2 = _seed(db_session, with_test_file=True, seq=1)
    sig2 = compute_signals(db_session, repo2.id, _CHANGED)
    assert sig2.has_tests is True


def test_risk_worker_creates_findings(db_session):
    repo = _seed(db_session)
    ai = FakeAI(
        {
            "risk_level": "high",
            "summary": "Touches payment charging without tests",
            "untested_scenarios": ["duplicate charge", "gateway timeout"],
        }
    )
    files = [
        _CHANGED,
        ChangedFile("README.md", "modified", "docs", 1, 1),  # not source -> skipped
        ChangedFile("tests/test_payment.py", "modified", "t", 1, 1),  # test -> skipped
    ]
    count = run_risk_analysis_job(repo.id, 21, db=db_session, pr_files=files, ai=ai)
    assert count == 1

    finding = db_session.execute(
        select(RiskFinding).where(RiskFinding.path == "src/payment.py")
    ).scalar_one()
    assert finding.risk_level == DriftSeverity.high
    assert finding.evidence["has_tests"] is False
    assert "duplicate charge" in finding.evidence["untested_scenarios"]

    job = db_session.execute(select(AnalysisJob)).scalars().all()[-1]
    assert job.status == JobStatus.succeeded


def test_risk_worker_no_source_files(db_session):
    repo = _seed(db_session)
    ai = FakeAI({"risk_level": "high", "summary": "x"})
    count = run_risk_analysis_job(
        repo.id, 22, db=db_session, pr_files=[ChangedFile("README.md", "modified", "d", 1, 1)],
        ai=ai,
    )
    assert count == 0
    assert db_session.execute(select(RiskFinding)).scalars().all() == []


def test_risk_worker_supersedes_prior(db_session):
    repo = _seed(db_session)
    ai = FakeAI({"risk_level": "medium", "summary": "s", "untested_scenarios": []})
    run_risk_analysis_job(repo.id, 30, db=db_session, pr_files=[_CHANGED], ai=ai)
    run_risk_analysis_job(repo.id, 30, db=db_session, pr_files=[_CHANGED], ai=ai)
    findings = db_session.execute(select(RiskFinding)).scalars().all()
    assert len(findings) == 1


def test_risk_worker_fails_without_ai(db_session):
    repo = _seed(db_session)
    result = run_risk_analysis_job(
        repo.id, 31, db=db_session, pr_files=[_CHANGED], ai=FakeAI({}, available=False)
    )
    assert result is None
    job = db_session.execute(select(AnalysisJob)).scalar_one()
    assert job.status == JobStatus.failed


def test_analyze_risk_endpoint(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo = _seed(db_session, owner_id=user.id)
    calls: list[tuple] = []
    monkeypatch.setattr(
        "app.api.routes.repositories.run_risk_analysis_job",
        lambda *a, **k: calls.append((a, k)),
    )
    resp = api_client.post(f"/api/v1/repositories/{repo.id}/analyze-risk", json={"pr_number": 5})
    assert resp.status_code == 202
    assert calls and calls[0][0] == (repo.id, 5)


def test_risk_findings_endpoint_requires_auth(client):
    assert client.get("/api/v1/repositories/1/risk-findings").status_code == 401
