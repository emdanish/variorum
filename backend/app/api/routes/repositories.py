from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.routes.analysis import finding_to_response
from app.core.logging import get_logger
from app.models import (
    AnalysisJob,
    CodeSymbol,
    Document,
    DriftFinding,
    GitHubInstallation,
    IndexingStatus,
    Repository,
    User,
)
from app.schemas import FindingResponse, JobResponse, RepositoryDetail, RepositoryResponse
from app.workers.indexing import run_index_job

logger = get_logger("variorum.repositories")
router = APIRouter(prefix="/repositories", tags=["repositories"])


def _to_response(repo: Repository) -> RepositoryResponse:
    return RepositoryResponse(
        id=repo.id,
        installation_id=repo.installation_id,
        full_name=repo.full_name,
        default_branch=repo.default_branch,
        private=repo.private,
        indexing_status=repo.indexing_status.value,
        last_indexed_at=repo.last_indexed_at,
    )


def _user_repo_query(user_id: int):
    return (
        select(Repository)
        .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
        .where(GitHubInstallation.owner_user_id == user_id)
    )


def _get_owned_repo(db: Session, user_id: int, repo_id: int) -> Repository:
    repo = db.execute(
        _user_repo_query(user_id).where(Repository.id == repo_id)
    ).scalar_one_or_none()
    if repo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repo


@router.get("", response_model=list[RepositoryResponse])
def list_repositories(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RepositoryResponse]:
    rows = db.execute(_user_repo_query(user.id).order_by(Repository.full_name)).scalars().all()
    return [_to_response(r) for r in rows]


@router.get("/{repo_id}", response_model=RepositoryDetail)
def get_repository(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepositoryDetail:
    repo = _get_owned_repo(db, user.id, repo_id)
    symbol_count = db.scalar(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.repository_id == repo.id)
    )
    document_count = db.scalar(
        select(func.count()).select_from(Document).where(Document.repository_id == repo.id)
    )
    base = _to_response(repo)
    return RepositoryDetail(
        **base.model_dump(),
        symbol_count=symbol_count or 0,
        document_count=document_count or 0,
    )


@router.get("/{repo_id}/jobs", response_model=list[JobResponse])
def list_jobs(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[JobResponse]:
    repo = _get_owned_repo(db, user.id, repo_id)
    jobs = (
        db.execute(
            select(AnalysisJob)
            .where(AnalysisJob.repository_id == repo.id)
            .order_by(AnalysisJob.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [
        JobResponse(
            id=j.id,
            type=j.type.value,
            status=j.status.value,
            trigger=j.trigger.value,
            external_ref=j.external_ref,
            error=j.error,
            created_at=j.created_at,
            started_at=j.started_at,
            finished_at=j.finished_at,
        )
        for j in jobs
    ]


@router.get("/{repo_id}/findings", response_model=list[FindingResponse])
def list_findings(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FindingResponse]:
    repo = _get_owned_repo(db, user.id, repo_id)
    rows = (
        db.execute(
            select(DriftFinding)
            .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
            .where(AnalysisJob.repository_id == repo.id)
            .order_by(DriftFinding.created_at.desc())
        )
        .scalars()
        .all()
    )
    return [finding_to_response(f) for f in rows]


@router.post("/{repo_id}/connect", response_model=RepositoryResponse)
def connect_repository(
    repo_id: int,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepositoryResponse:
    """Queue a repository for indexing and kick off the ingestion worker."""
    repo = _get_owned_repo(db, user.id, repo_id)
    if repo.indexing_status == IndexingStatus.indexing:
        return _to_response(repo)

    repo.indexing_status = IndexingStatus.pending
    db.commit()
    db.refresh(repo)
    background_tasks.add_task(run_index_job, repo.id)
    logger.info("repository queued for indexing id=%s full_name=%s", repo.id, repo.full_name)
    return _to_response(repo)
