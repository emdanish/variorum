from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy.orm import Session

from app.ai.embeddings import get_embedding_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import GitHubInstallation, Repository
from app.services.github.auth import GitHubAppAuth
from app.services.github.client import GitHubClient, HistoryItem
from app.services.knowledge import embed_missing, store_items
from app.services.metrics import FileChangeRecord, is_fix_message, store_file_changes

logger = get_logger("variorum.ingest")

# Bounds on how much history to pull per repository (keeps API + storage sane).
MAX_COMMITS = 100
MAX_PULL_REQUESTS = 50
MAX_ISSUES = 50
# Per-commit file detail is one API call each, so churn collection is bounded
# more tightly than the history listing.
CHURN_MAX_COMMITS = 60


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


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

    gh: GitHubClient | None = client
    installation_id: int | None = None
    try:
        installation = db.get(GitHubInstallation, repo.installation_id)
        installation_id = installation.installation_id if installation else None
        if items is None:
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

        changes = 0
        if gh is not None and installation_id is not None:
            try:
                changes = _collect_file_changes(db, repo, gh, installation_id, items)
            except Exception as exc:  # noqa: BLE001 — churn collection is best-effort
                logger.warning("file-change collection failed repo=%s: %s", repo.full_name, exc)

        logger.info(
            "ingested history repo=%s entries=%d embedded=%d file_changes=%d",
            repo.full_name,
            stored,
            embedded,
            changes,
        )
        return stored
    except Exception as exc:  # noqa: BLE001 — never crash the worker
        db.rollback()
        logger.warning("history ingest failed repo_id=%s: %s", repository_id, exc)
        return None


def _collect_file_changes(
    db: Session,
    repo: Repository,
    gh: GitHubClient,
    installation_id: int,
    items: list[HistoryItem],
) -> int:
    commits = [i for i in items if i.kind == "commit" and i.source_ref][:CHURN_MAX_COMMITS]
    if not commits:
        return 0
    records = asyncio.run(_fetch_file_changes(gh, installation_id, repo.full_name, commits))
    return store_file_changes(db, repo.id, records)


async def _fetch_file_changes(
    gh: GitHubClient, installation_id: int, full_name: str, commits: list[HistoryItem]
) -> list[FileChangeRecord]:
    records: list[FileChangeRecord] = []
    for item in commits:
        files = await gh.get_commit_files(installation_id, full_name, item.source_ref)
        is_fix = is_fix_message(item.title or item.body)
        occurred = _parse_iso(item.occurred_at)
        records.extend(
            FileChangeRecord(
                commit_sha=item.source_ref,
                path=f.path,
                author=item.author,
                additions=f.additions,
                deletions=f.deletions,
                is_fix=is_fix,
                occurred_at=occurred,
            )
            for f in files
        )
    return records


async def _fetch_history(
    gh: GitHubClient, installation_id: int, full_name: str
) -> list[HistoryItem]:
    commits = await gh.list_commits(installation_id, full_name, max_items=MAX_COMMITS)
    prs = await gh.list_pull_requests(installation_id, full_name, max_items=MAX_PULL_REQUESTS)
    issues = await gh.list_issues(installation_id, full_name, max_items=MAX_ISSUES)
    return [*commits, *prs, *issues]
