from __future__ import annotations

from sqlalchemy import select

from app.models import (
    AnalysisJob,
    CodeSymbol,
    DocCodeLink,
    Document,
    DriftFinding,
    FindingStatus,
    GitHubInstallation,
    JobStatus,
    JobTrigger,
    JobType,
    Repository,
    RiskFinding,
    Suppression,
    User,
)
from app.services import suppressions as svc
from app.services.github.client import ChangedFile
from app.workers.pr_analysis import run_pr_analysis_job
from app.workers.risk_analysis import run_risk_analysis_job
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


def _repo(db, owner_id=None, seq=0) -> Repository:
    if owner_id is None:
        u = User(email=f"sup{seq}@example.com", github_user_id=7400 + seq)
        db.add(u)
        db.flush()
        owner_id = u.id
    inst = GitHubInstallation(
        installation_id=8400 + seq, account_login="acme", account_type="User",
        owner_user_id=owner_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8401 + seq, full_name=f"acme/s{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


def test_suppress_is_idempotent_and_scoped(db_session):
    repo = _repo(db_session, seq=0)
    svc.suppress(db_session, repo.id, svc.DRIFT, "docs/a.md")
    svc.suppress(db_session, repo.id, svc.DRIFT, "docs/a.md")  # no duplicate
    assert svc.suppressed_targets(db_session, repo.id, svc.DRIFT) == {"docs/a.md"}
    assert svc.suppressed_targets(db_session, repo.id, svc.RISK) == set()
    rows = db_session.execute(
        select(Suppression).where(Suppression.repository_id == repo.id)
    ).scalars().all()
    assert len(rows) == 1

    svc.unsuppress(db_session, repo.id, svc.DRIFT, "docs/a.md")
    assert svc.suppressed_targets(db_session, repo.id, svc.DRIFT) == set()


# --------------------------------------------------------------------------- #
# Worker skip — the payoff: dismissed targets don't come back
# --------------------------------------------------------------------------- #


def _seed_drift(db) -> tuple[Repository, Document]:
    repo = _repo(db, seq=1)
    sym = CodeSymbol(
        repository_id=repo.id, path="src/auth.py", language="python", kind="function", name="login"
    )
    db.add(sym)
    db.flush()
    doc = Document(repository_id=repo.id, path="docs/auth.md", title="Auth")
    db.add(doc)
    db.flush()
    db.add(DocCodeLink(document_id=doc.id, symbol_id=sym.id, path="src/auth.py", confidence=0.6))
    db.flush()
    return repo, doc


_PR_FILES = [
    ChangedFile(path="src/auth.py", status="modified", patch="@@\n-a\n+b", additions=1, deletions=1)
]
_DRIFT_AI = FakeAI(
    {"drifted": True, "severity": "high", "summary": "Auth changed", "evidence": []}
)


def test_drift_worker_skips_suppressed_doc(db_session):
    repo, doc = _seed_drift(db_session)
    svc.suppress(db_session, repo.id, svc.DRIFT, "docs/auth.md")
    count = run_pr_analysis_job(
        repo.id, 42, db=db_session, pr_files=_PR_FILES,
        doc_fetcher=lambda _p: "Auth uses cookies.", ai=_DRIFT_AI,
    )
    assert count == 0  # would have been 1 without the suppression
    assert db_session.execute(
        select(DriftFinding).where(DriftFinding.document_id == doc.id)
    ).scalars().all() == []


_CHANGED = ChangedFile(
    path="src/payment.py", status="modified", patch="@@\n+x", additions=20, deletions=3
)
_RISK_AI = FakeAI({"risk_level": "high", "summary": "Risky", "untested_scenarios": ["x"]})


def test_risk_worker_skips_suppressed_path(db_session):
    repo = _repo(db_session, seq=2)
    db_session.add(
        CodeSymbol(repository_id=repo.id, path="src/payment.py", language="python",
                   kind="function", name="charge")
    )
    db_session.flush()
    svc.suppress(db_session, repo.id, svc.RISK, "src/payment.py")
    count = run_risk_analysis_job(repo.id, 21, db=db_session, pr_files=[_CHANGED], ai=_RISK_AI)
    assert count == 0
    assert db_session.execute(select(RiskFinding)).scalars().all() == []


# --------------------------------------------------------------------------- #
# Dismiss creates a suppression; restore lifts it
# --------------------------------------------------------------------------- #


def _drift_finding(db, repo, doc_path="docs/x.md") -> DriftFinding:
    job = AnalysisJob(
        repository_id=repo.id, type=JobType.pr_analysis, status=JobStatus.succeeded,
        trigger=JobTrigger.manual,
    )
    db.add(job)
    db.flush()
    f = DriftFinding(
        analysis_job_id=job.id, severity="high", summary="d",
        evidence={"document_path": doc_path, "pr_number": 5}, status=FindingStatus.detected,
    )
    db.add(f)
    db.flush()
    return f


def test_dismiss_drift_suppresses_restore_lifts(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, owner_id=user.id, seq=3)
    f = _drift_finding(db_session, repo, "docs/auth.md")

    api_client.post(f"/api/v1/findings/{f.id}/dismiss").raise_for_status()
    assert svc.suppressed_targets(db_session, repo.id, svc.DRIFT) == {"docs/auth.md"}

    api_client.post(f"/api/v1/findings/{f.id}/restore").raise_for_status()
    assert svc.suppressed_targets(db_session, repo.id, svc.DRIFT) == set()


def test_dismiss_risk_suppresses_restore_lifts(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, owner_id=user.id, seq=4)
    job = AnalysisJob(
        repository_id=repo.id, type=JobType.pr_analysis, status=JobStatus.succeeded,
        trigger=JobTrigger.manual,
    )
    db_session.add(job)
    db_session.flush()
    rf = RiskFinding(
        analysis_job_id=job.id, path="src/pay.py", risk_level="high", summary="r",
        evidence={"path": "src/pay.py"}, status="open",
    )
    db_session.add(rf)
    db_session.flush()

    api_client.post(f"/api/v1/risk-findings/{rf.id}/dismiss").raise_for_status()
    assert svc.suppressed_targets(db_session, repo.id, svc.RISK) == {"src/pay.py"}

    api_client.post(f"/api/v1/risk-findings/{rf.id}/restore").raise_for_status()
    assert svc.suppressed_targets(db_session, repo.id, svc.RISK) == set()
