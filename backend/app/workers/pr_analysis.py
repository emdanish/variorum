from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai.service import AIService, get_ai_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import (
    AnalysisJob,
    DriftFinding,
    FindingStatus,
    GitHubInstallation,
    JobStatus,
    JobTrigger,
    JobType,
    Repository,
)
from app.services.analysis.drift import ChangedFileDiff, DriftVerdict, assess_document_drift
from app.services.analysis.pr_context import DriftCandidate, build_candidates
from app.services.github.auth import GitHubAppAuth
from app.services.github.client import ChangedFile, GitHubClient

logger = get_logger("variorum.pr_analysis")

DocFetcher = Callable[[str], str | None]
MAX_CANDIDATE_DOCS = 10


def run_pr_analysis_job(
    repository_id: int,
    pr_number: int,
    *,
    head_sha: str | None = None,
    db: Session | None = None,
    pr_files: list[ChangedFile] | None = None,
    doc_fetcher: DocFetcher | None = None,
    ai: AIService | None = None,
    max_docs: int = MAX_CANDIDATE_DOCS,
) -> int | None:
    """Analyze a pull request for documentation drift. Returns the number of
    drift findings, or None if the job could not run. `db`, `pr_files`,
    `doc_fetcher`, and `ai` are injectable for testing."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return _run(
            session, repository_id, pr_number, head_sha, pr_files, doc_fetcher, ai, max_docs
        )
    finally:
        if owns_session:
            session.close()


def _run(
    db: Session,
    repository_id: int,
    pr_number: int,
    head_sha: str | None,
    pr_files: list[ChangedFile] | None,
    doc_fetcher: DocFetcher | None,
    ai: AIService | None,
    max_docs: int,
) -> int | None:
    repo = db.get(Repository, repository_id)
    if repo is None:
        logger.warning("pr analysis: repository %s not found", repository_id)
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

    try:
        ai_service = ai or get_ai_service()
        if not ai_service.available:
            raise RuntimeError("no AI provider configured")
        installation = db.get(GitHubInstallation, repo.installation_id)
        if installation is None:
            raise RuntimeError("installation missing for repository")

        assessed = asyncio.run(
            _analyze(
                db=db,
                repo=repo,
                installation_id=installation.installation_id,
                pr_number=pr_number,
                head_sha=head_sha or repo.default_branch,
                pr_files=pr_files,
                doc_fetcher=doc_fetcher,
                ai=ai_service,
                max_docs=max_docs,
            )
        )

        findings = 0
        for candidate, verdict in assessed:
            if not verdict.drifted:
                continue
            db.add(
                DriftFinding(
                    analysis_job_id=job.id,
                    document_id=candidate.document_id,
                    severity=verdict.severity,
                    summary=verdict.summary,
                    status=FindingStatus.detected,
                    evidence={
                        "pr_number": pr_number,
                        "document_path": candidate.document_path,
                        "trigger_files": candidate.trigger_paths,
                        "affected_symbols": candidate.symbol_names,
                        "drift_evidence": verdict.evidence,
                        "suggested_update": verdict.suggested_update,
                        "provider": verdict.provider,
                        "model": verdict.model,
                    },
                )
            )
            findings += 1

        job.status = JobStatus.succeeded
        job.finished_at = datetime.now(UTC)
        db.commit()
        logger.info(
            "pr analysis done repo=%s pr=%s findings=%d", repo.full_name, pr_number, findings
        )
        return findings
    except Exception as exc:  # noqa: BLE001 — record failure on the job, never crash the worker
        db.rollback()
        failed_job = db.get(AnalysisJob, job_id)
        if failed_job is not None:
            failed_job.status = JobStatus.failed
            failed_job.error = str(exc)[:2000]
            failed_job.finished_at = datetime.now(UTC)
        db.commit()
        logger.warning("pr analysis failed repo_id=%s pr=%s: %s", repository_id, pr_number, exc)
        return None


async def _analyze(
    *,
    db: Session,
    repo: Repository,
    installation_id: int,
    pr_number: int,
    head_sha: str,
    pr_files: list[ChangedFile] | None,
    doc_fetcher: DocFetcher | None,
    ai: AIService,
    max_docs: int,
) -> list[tuple[DriftCandidate, DriftVerdict]]:
    client: GitHubClient | None = None
    if pr_files is None:
        client = GitHubClient(GitHubAppAuth(get_settings()))
        pr_files = await client.list_pull_request_files(
            installation_id, repo.full_name, pr_number
        )

    patch_by_path = {f.path: f.patch for f in pr_files}
    changed_paths = {f.path for f in pr_files}
    candidates = build_candidates(db, repo.id, changed_paths)
    if len(candidates) > max_docs:
        logger.info(
            "pr analysis capped candidates repo=%s pr=%s %d->%d",
            repo.full_name,
            pr_number,
            len(candidates),
            max_docs,
        )
        candidates = candidates[:max_docs]

    results: list[tuple[DriftCandidate, DriftVerdict]] = []
    for candidate in candidates:
        if doc_fetcher is not None:
            content = doc_fetcher(candidate.document_path)
        else:
            if client is None:
                client = GitHubClient(GitHubAppAuth(get_settings()))
            content = await client.get_file_text(
                installation_id, repo.full_name, candidate.document_path, head_sha
            )
        if not content:
            continue
        diffs = [
            ChangedFileDiff(path=path, patch=patch_by_path.get(path))
            for path in candidate.trigger_paths
        ]
        verdict = await assess_document_drift(
            ai,
            doc_path=candidate.document_path,
            doc_content=content,
            affected_symbols=candidate.symbol_names,
            diffs=diffs,
        )
        results.append((candidate, verdict))
    return results
