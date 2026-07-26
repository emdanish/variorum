from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import GitHubInstallation, Repository
from app.services.github.client import GitHubClient, RepoInfo


def upsert_installation(
    db: Session,
    *,
    installation_id: int,
    account_login: str,
    account_type: str,
    suspended: bool = False,
    owner_user_id: int | None = None,
) -> GitHubInstallation:
    inst = db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.installation_id == installation_id
        )
    ).scalar_one_or_none()

    if inst is None:
        inst = GitHubInstallation(
            installation_id=installation_id,
            account_login=account_login,
            account_type=account_type,
            owner_user_id=owner_user_id,
        )
        db.add(inst)
    else:
        inst.account_login = account_login
        inst.account_type = account_type
        if owner_user_id is not None:
            inst.owner_user_id = owner_user_id

    inst.suspended_at = datetime.now(UTC) if suspended else None
    db.flush()
    return inst


def upsert_repository(db: Session, installation: GitHubInstallation, repo: RepoInfo) -> Repository:
    existing = db.execute(
        select(Repository).where(Repository.github_repo_id == repo.github_repo_id)
    ).scalar_one_or_none()

    if existing is None:
        existing = Repository(
            installation_id=installation.id,
            github_repo_id=repo.github_repo_id,
            full_name=repo.full_name,
            default_branch=repo.default_branch,
            private=repo.private,
        )
        db.add(existing)
    else:
        existing.installation_id = installation.id
        existing.full_name = repo.full_name
        existing.default_branch = repo.default_branch
        existing.private = repo.private

    db.flush()
    return existing


def prune_repositories(
    db: Session, installation: GitHubInstallation, keep_github_repo_ids: set[int]
) -> int:
    rows = db.execute(
        select(Repository).where(Repository.installation_id == installation.id)
    ).scalars().all()
    removed = 0
    for repo in rows:
        if repo.github_repo_id not in keep_github_repo_ids:
            db.delete(repo)
            removed += 1
    db.flush()
    return removed


def remove_repositories(
    db: Session, installation: GitHubInstallation, github_repo_ids: list[int]
) -> None:
    if not github_repo_ids:
        return
    db.execute(
        delete(Repository).where(
            Repository.installation_id == installation.id,
            Repository.github_repo_id.in_(github_repo_ids),
        )
    )
    db.flush()


async def sync_installation_via_api(
    db: Session,
    client: GitHubClient,
    installation_id: int,
    owner_user_id: int | None,
) -> GitHubInstallation:
    account = await client.get_installation(installation_id)
    inst = upsert_installation(
        db,
        installation_id=account.installation_id,
        account_login=account.account_login,
        account_type=account.account_type,
        suspended=account.suspended,
        owner_user_id=owner_user_id,
    )
    repos = await client.list_installation_repositories(installation_id)
    for repo in repos:
        upsert_repository(db, inst, repo)
    prune_repositories(db, inst, {r.github_repo_id for r in repos})
    db.commit()
    db.refresh(inst)
    return inst
