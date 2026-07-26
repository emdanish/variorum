from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.logging import get_logger
from app.models import GitHubInstallation, IndexingStatus, Repository, User
from app.schemas import RepositoryResponse

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
    rows = (
        db.execute(_user_repo_query(user.id).order_by(Repository.full_name)).scalars().all()
    )
    return [_to_response(r) for r in rows]


@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepositoryResponse:
    return _to_response(_get_owned_repo(db, user.id, repo_id))


@router.post("/{repo_id}/connect", response_model=RepositoryResponse)
def connect_repository(
    repo_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RepositoryResponse:
    """Queue a repository for indexing. The indexing worker (milestone M2) picks
    up repositories in the `pending` state."""
    repo = _get_owned_repo(db, user.id, repo_id)
    if repo.indexing_status != IndexingStatus.indexing:
        repo.indexing_status = IndexingStatus.pending
        db.commit()
        db.refresh(repo)
    logger.info("repository queued for indexing id=%s full_name=%s", repo.id, repo.full_name)
    return _to_response(repo)
