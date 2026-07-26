from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.ai.service import AIService, get_ai_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import (
    AnalysisJob,
    GitHubInstallation,
    JobStatus,
    JobTrigger,
    JobType,
    Repository,
    RiskFinding,
)
from app.services.analysis.risk import (
    FileSignals,
    RiskVerdict,
    assess_risk,
    compute_signals,
    is_source_path,
)
from app.services.github.auth import GitHubAppAuth
from app.services.github.client import ChangedFile, GitHubClient

logger = get_logger("variorum.risk_analysis")
MAX_FILES = 10


def run_risk_analysis_job(
    repository_id: int,
    pr_number: int,
    *,
    db: Session | None = None,
    pr_files: list[ChangedFile] | None = None,
    ai: AIService | None = None,
    max_files: int = MAX_FILES,
) -> int | None:
    """Assess the test-risk of a pull request's changed source files. Returns the
    number of risk findings. `db`, `pr_files`, `ai` are injectable for testing."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return _run(session, repository_id, pr_number, pr_files, ai, max_files)
    finally:
        if owns_session:
            session.close()


def _supersede_prior(db: Session, repository_id: int, pr_number: int, keep_job_id: int) -> None:
    prior = (
        db.execute(
            select(RiskFinding.id)
            .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
            .where(
                AnalysisJob.repository_id == repository_id,
                AnalysisJob.id != keep_job_id,
                RiskFinding.evidence["pr_number"].astext == str(pr_number),
            )
        )
        .scalars()
        .all()
    )
    if prior:
        db.execute(delete(RiskFinding).where(RiskFinding.id.in_(prior)))
        db.commit()


def _run(
    db: Session,
    repository_id: int,
    pr_number: int,
    pr_files: list[ChangedFile] | None,
    ai: AIService | None,
    max_files: int,
) -> int | None:
    repo = db.get(Repository, repository_id)
    if repo is None:
        logger.warning("risk analysis: repository %s not found", repository_id)
        return None

    job = AnalysisJob(
        repository_id=repo.id,
        type=JobType.pr_analysis,
        status=JobStatus.running,
        trigger=JobTrigger.webhook,
        external_ref=str(pr_number),
        started_at=datetime.now(UTC),
    )
    db.add(job)
    db.commit()
    job_id = job.id
    _supersede_prior(db, repo.id, pr_number, keep_job_id=job.id)

    try:
        ai_service = ai or get_ai_service()
        if not ai_service.available:
            raise RuntimeError("no AI provider configured")
        installation = db.get(GitHubInstallation, repo.installation_id)
        if installation is None:
            raise RuntimeError("installation missing for repository")

        if pr_files is None:
            client = GitHubClient(GitHubAppAuth(get_settings()))
            pr_files = asyncio.run(
                client.list_pull_request_files(
                    installation.installation_id, repo.full_name, pr_number
                )
            )
        source = [f for f in pr_files if is_source_path(f.path)][:max_files]

        assessed, errors = asyncio.run(_assess_all(db, repo.id, source, ai_service, pr_number))
        if errors and not assessed:
            raise RuntimeError(f"all {errors} file assessment(s) failed")

        for changed, verdict, signals in assessed:
            db.add(
                RiskFinding(
                    analysis_job_id=job.id,
                    path=changed.path,
                    risk_level=verdict.risk_level,
                    summary=verdict.summary,
                    evidence={
                        "pr_number": pr_number,
                        "path": changed.path,
                        "churn": signals.churn,
                        "has_tests": signals.has_tests,
                        "symbol_count": signals.symbol_count,
                        "untested_scenarios": verdict.untested_scenarios,
                        "provider": verdict.provider,
                        "model": verdict.model,
                    },
                )
            )

        job.status = JobStatus.succeeded
        job.finished_at = datetime.now(UTC)
        db.commit()
        logger.info(
            "risk analysis done repo=%s pr=%s findings=%d", repo.full_name, pr_number, len(assessed)
        )
        return len(assessed)
    except Exception as exc:  # noqa: BLE001 — record failure on the job, never crash
        db.rollback()
        failed_job = db.get(AnalysisJob, job_id)
        if failed_job is not None:
            failed_job.status = JobStatus.failed
            failed_job.error = str(exc)[:2000]
            failed_job.finished_at = datetime.now(UTC)
        db.commit()
        logger.warning("risk analysis failed repo_id=%s pr=%s: %s", repository_id, pr_number, exc)
        return None


async def _assess_all(
    db: Session, repository_id: int, files: list[ChangedFile], ai: AIService, pr_number: int
) -> tuple[list[tuple[ChangedFile, RiskVerdict, FileSignals]], int]:
    results: list[tuple[ChangedFile, RiskVerdict, FileSignals]] = []
    errors = 0
    for changed in files:
        try:
            signals = compute_signals(db, repository_id, changed)
            verdict = await assess_risk(ai, path=changed.path, patch=changed.patch, signals=signals)
            results.append((changed, verdict, signals))
        except Exception as exc:  # noqa: BLE001 — isolate per-file failures
            errors += 1
            logger.warning(
                "risk assessment failed file=%s pr=%s: %s", changed.path, pr_number, exc
            )
    return results, errors
