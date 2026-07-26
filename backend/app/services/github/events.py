from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import GitHubInstallation
from app.services.github.client import RepoInfo
from app.services.installations import (
    remove_repositories,
    upsert_installation,
    upsert_repository,
)

logger = get_logger("variorum.gh_events")


def _repo_from_payload(raw: dict) -> RepoInfo:
    return RepoInfo(
        github_repo_id=raw["id"],
        full_name=raw["full_name"],
        default_branch=raw.get("default_branch") or "main",
        private=bool(raw.get("private", True)),
    )


def _get_installation(db: Session, installation_id: int) -> GitHubInstallation | None:
    return db.execute(
        select(GitHubInstallation).where(
            GitHubInstallation.installation_id == installation_id
        )
    ).scalar_one_or_none()


def dispatch_webhook(db: Session, event: str, payload: dict) -> str:
    """Route a verified webhook to its handler. Returns a short description of
    the action taken (useful for logs/tests). Unknown events are acknowledged."""
    if event == "installation":
        return _handle_installation(db, payload)
    if event == "installation_repositories":
        return _handle_installation_repositories(db, payload)
    if event in {"pull_request", "push"}:
        # Analysis is wired in milestone M3.
        return f"acknowledged:{event}"
    return f"ignored:{event}"


def _handle_installation(db: Session, payload: dict) -> str:
    action = payload.get("action", "")
    inst_payload = payload.get("installation", {})
    installation_id = inst_payload.get("id")
    if installation_id is None:
        return "installation:missing_id"

    if action == "deleted":
        existing = _get_installation(db, installation_id)
        if existing is not None:
            db.delete(existing)
            db.commit()
        return "installation:deleted"

    account = inst_payload.get("account", {})
    suspended = action == "suspend" or bool(inst_payload.get("suspended_at"))
    inst = upsert_installation(
        db,
        installation_id=installation_id,
        account_login=account.get("login", "unknown"),
        account_type=account.get("type", "User"),
        suspended=suspended,
    )
    for raw in payload.get("repositories", []):
        upsert_repository(db, inst, _repo_from_payload(raw))
    db.commit()
    return f"installation:{action or 'synced'}"


def _handle_installation_repositories(db: Session, payload: dict) -> str:
    installation_id = payload.get("installation", {}).get("id")
    if installation_id is None:
        return "installation_repositories:missing_id"
    inst = _get_installation(db, installation_id)
    if inst is None:
        account = payload.get("installation", {}).get("account", {})
        inst = upsert_installation(
            db,
            installation_id=installation_id,
            account_login=account.get("login", "unknown"),
            account_type=account.get("type", "User"),
        )

    added = payload.get("repositories_added", [])
    for raw in added:
        upsert_repository(db, inst, _repo_from_payload(raw))

    removed_ids = [r["id"] for r in payload.get("repositories_removed", [])]
    remove_repositories(db, inst, removed_ids)

    db.commit()
    return f"installation_repositories:+{len(added)}/-{len(removed_ids)}"
