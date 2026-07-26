from __future__ import annotations

from sqlalchemy import select

from app.models import (
    AnalysisJob,
    CodeSymbol,
    DocCodeLink,
    Document,
    DriftFinding,
    DriftSeverity,
    GitHubInstallation,
    JobStatus,
    JobType,
    LinkSource,
    Repository,
    User,
)
from app.services.github.client import ChangedFile
from app.workers.pr_analysis import run_pr_analysis_job
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


def _seed(db) -> tuple[Repository, Document]:
    user = User(email="pr@example.com", github_user_id=987)
    db.add(user)
    db.flush()
    inst = GitHubInstallation(
        installation_id=7700, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=7701, full_name="acme/app", default_branch="main"
    )
    db.add(repo)
    db.flush()
    symbol = CodeSymbol(
        repository_id=repo.id, path="src/auth.py", language="python", kind="function", name="login"
    )
    db.add(symbol)
    db.flush()
    doc = Document(repository_id=repo.id, path="docs/auth.md", title="Auth")
    db.add(doc)
    db.flush()
    db.add(
        DocCodeLink(
            document_id=doc.id,
            symbol_id=symbol.id,
            path="src/auth.py",
            confidence=0.6,
            source=LinkSource.heuristic,
        )
    )
    db.flush()
    return repo, doc


_PR_FILES = [
    ChangedFile(
        path="src/auth.py",
        status="modified",
        patch="@@\n-cookie\n+jwt",
        additions=1,
        deletions=1,
    )
]


def test_worker_creates_finding_on_drift(db_session):
    repo, doc = _seed(db_session)
    ai = FakeAI(
        {
            "drifted": True,
            "severity": "high",
            "summary": "Auth moved to JWT",
            "evidence": ["diff shows jwt"],
            "suggested_update": "Document JWT.",
        }
    )
    count = run_pr_analysis_job(
        repo.id,
        42,
        db=db_session,
        pr_files=_PR_FILES,
        doc_fetcher=lambda _p: "Auth uses session cookies.",
        ai=ai,
    )
    assert count == 1

    finding = db_session.execute(
        select(DriftFinding).where(DriftFinding.document_id == doc.id)
    ).scalar_one()
    assert finding.severity == DriftSeverity.high
    assert finding.evidence["pr_number"] == 42
    assert finding.evidence["provider"] == "gemini-1"
    assert finding.evidence["trigger_files"] == ["src/auth.py"]

    job = db_session.execute(
        select(AnalysisJob).where(AnalysisJob.repository_id == repo.id)
    ).scalar_one()
    assert job.type == JobType.pr_analysis
    assert job.status == JobStatus.succeeded
    assert job.external_ref == "42"


def test_worker_no_drift_creates_no_findings(db_session):
    repo, _ = _seed(db_session)
    ai = FakeAI({"drifted": False, "severity": "info", "summary": "accurate"})
    count = run_pr_analysis_job(
        repo.id, 43, db=db_session, pr_files=_PR_FILES, doc_fetcher=lambda _p: "content", ai=ai
    )
    assert count == 0
    assert db_session.execute(select(DriftFinding)).scalars().all() == []
    job = db_session.execute(select(AnalysisJob)).scalar_one()
    assert job.status == JobStatus.succeeded


def test_worker_skips_when_doc_content_missing(db_session):
    repo, _ = _seed(db_session)
    ai = FakeAI({"drifted": True, "severity": "high", "summary": "x"})
    count = run_pr_analysis_job(
        repo.id, 44, db=db_session, pr_files=_PR_FILES, doc_fetcher=lambda _p: None, ai=ai
    )
    assert count == 0
    assert ai.calls == []  # AI never consulted when the doc can't be fetched


def test_worker_fails_without_ai_provider(db_session):
    repo, _ = _seed(db_session)
    ai = FakeAI({}, available=False)
    result = run_pr_analysis_job(
        repo.id, 45, db=db_session, pr_files=_PR_FILES, doc_fetcher=lambda _p: "c", ai=ai
    )
    assert result is None
    job = db_session.execute(select(AnalysisJob)).scalar_one()
    assert job.status == JobStatus.failed
    assert job.error and "AI provider" in job.error
