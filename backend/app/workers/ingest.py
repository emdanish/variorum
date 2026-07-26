from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.ai.embeddings import get_embedding_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import GitHubInstallation, Repository
from app.services.github.auth import GitHubAppAuth
from app.services.github.client import GitHubClient, HistoryItem
from app.services.knowledge import embed_missing, store_items

logger = get_logger("variorum.ingest")

# Bounds on how much history to pull per repository (keeps API + storage sane).
MAX_COMMITS = 100
MAX_PULL_REQUESTS = 50
MAX_ISSUES = 50


def run_ingest_history_job(
    repository_id: int,
    *,
    db: Session | None = None,
    client: GitHubClient | None = None,
    items: list[HistoryItem] | None = None,
) -> int | None:
    """Ingest commit / PR / issue history for a repository into knowledge
    entries. `db`, `client`, and `items` are injectable for testing."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return _run(session, repository_id, client, items)
    finally:
        if owns_session:
            session.close()


def _run(
    db: Session,
    repository_id: int,
    client: GitHubClient | None,
    items: list[HistoryItem] | None,
) -> int | None:
    repo = db.get(Repository, repository_id)
    if repo is None:
        logger.warning("ingest: repository %s not found", repository_id)
        return None

    try:
        if items is None:
            installation = db.get(GitHubInstallation, repo.installation_id)
            if installation is None:
                raise RuntimeError("installation missing for repository")
            gh = client or GitHubClient(GitHubAppAuth(get_settings()))
            items = asyncio.run(_fetch_history(gh, installation.installation_id, repo.full_name))

        stored = store_items(db, repo.id, items)
        db.commit()
        try:
            embedded = embed_missing(db, repo.id, get_embedding_service())
        except Exception as exc:  # noqa: BLE001 — embeddings are best-effort
            embedded = 0
            logger.warning("embedding step failed repo=%s: %s", repo.full_name, exc)
        logger.info(
            "ingested history repo=%s entries=%d embedded=%d", repo.full_name, stored, embedded
        )
        return stored
    except Exception as exc:  # noqa: BLE001 — never crash the worker
        db.rollback()
        logger.warning("history ingest failed repo_id=%s: %s", repository_id, exc)
        return None


async def _fetch_history(
    gh: GitHubClient, installation_id: int, full_name: str
) -> list[HistoryItem]:
    commits = await gh.list_commits(installation_id, full_name, max_items=MAX_COMMITS)
    prs = await gh.list_pull_requests(installation_id, full_name, max_items=MAX_PULL_REQUESTS)
    issues = await gh.list_issues(installation_id, full_name, max_items=MAX_ISSUES)
    return [*commits, *prs, *issues]
