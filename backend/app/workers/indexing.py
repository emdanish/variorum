from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import (
    AnalysisJob,
    GitHubInstallation,
    IndexingStatus,
    JobStatus,
    JobTrigger,
    JobType,
    Repository,
)
from app.services.github.auth import GitHubAppAuth
from app.services.indexer.archive import download_and_extract
from app.services.indexer.pipeline import IndexResult, reindex_repository

logger = get_logger("variorum.indexing")

Indexer = Callable[[Session, Repository, Path], IndexResult]


def run_index_job(
    repository_id: int,
    *,
    db: Session | None = None,
    source_root: Path | None = None,
    indexer: Indexer = reindex_repository,
) -> IndexResult | None:
    """Index a repository, tracking progress in an AnalysisJob and the repo's
    indexing_status. Runs as a FastAPI BackgroundTask in production; `db` and
    `source_root` are injectable for testing."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return _run(session, repository_id, source_root, indexer)
    finally:
        if owns_session:
            session.close()


def _run(
    db: Session,
    repository_id: int,
    source_root: Path | None,
    indexer: Indexer,
) -> IndexResult | None:
    repo = db.get(Repository, repository_id)
    if repo is None:
        logger.warning("index job: repository %s not found", repository_id)
        return None

    job = AnalysisJob(
        repository_id=repo.id,
        type=JobType.indexing,
        status=JobStatus.running,
        trigger=JobTrigger.manual,
        started_at=datetime.now(UTC),
    )
    db.add(job)
    repo.indexing_status = IndexingStatus.indexing
    db.commit()
    job_id = job.id

    try:
        if source_root is not None:
            result = indexer(db, repo, Path(source_root))
        else:
            result = _index_from_github(db, repo, indexer)

        repo.indexing_status = IndexingStatus.indexed
        repo.last_indexed_at = datetime.now(UTC)
        job.status = JobStatus.succeeded
        job.finished_at = datetime.now(UTC)
        db.commit()

        embedded = 0
        try:
            from app.ai.embeddings import get_embedding_service
            from app.services.symbols import embed_missing_symbols

            embedded = embed_missing_symbols(db, repo.id, get_embedding_service())
        except Exception as exc:  # noqa: BLE001 — code embeddings are best-effort
            logger.warning("symbol embedding failed repo=%s: %s", repo.full_name, exc)

        logger.info(
            "indexed repo=%s files=%d symbols=%d docs=%d links=%d embedded=%d",
            repo.full_name,
            result.files,
            result.symbols,
            result.documents,
            result.links,
            embedded,
        )
        return result
    except Exception as exc:  # noqa: BLE001 — record failure on the job, never crash the worker
        db.rollback()
        failed_repo = db.get(Repository, repository_id)
        failed_job = db.get(AnalysisJob, job_id)
        if failed_repo is not None:
            failed_repo.indexing_status = IndexingStatus.failed
        if failed_job is not None:
            failed_job.status = JobStatus.failed
            failed_job.error = str(exc)[:2000]
            failed_job.finished_at = datetime.now(UTC)
        db.commit()
        logger.warning("indexing failed repo_id=%s: %s", repository_id, exc)
        return None


def _index_from_github(db: Session, repo: Repository, indexer: Indexer) -> IndexResult:
    installation = db.get(GitHubInstallation, repo.installation_id)
    if installation is None:
        raise RuntimeError("installation missing for repository")
    auth = GitHubAppAuth(get_settings())
    with tempfile.TemporaryDirectory() as tmp:
        root = asyncio.run(
            download_and_extract(
                auth,
                installation.installation_id,
                repo.full_name,
                repo.default_branch,
                Path(tmp),
            )
        )
        return indexer(db, repo, root)
