from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models import (
    AnalysisJob,
    DriftFinding,
    FindingStatus,
    GitHubInstallation,
    Repository,
    RiskFinding,
)
from app.services import pr_comment as pr_comment_svc
from app.services import pr_impact as pr_impact_svc
from app.services.github.auth import GitHubAppAuth
from app.services.github.client import ChangedFile, GitHubClient

logger = get_logger("variorum.pr_comment")


def _open_drift_count(db: Session, repository_id: int, pr_number: int) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(DriftFinding)
            .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
            .where(
                AnalysisJob.repository_id == repository_id,
                DriftFinding.status == FindingStatus.detected,
                DriftFinding.evidence["pr_number"].astext == str(pr_number),
            )
        ).scalar()
        or 0
    )


def _open_risk_count(db: Session, repository_id: int, pr_number: int) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(RiskFinding)
            .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
            .where(
                AnalysisJob.repository_id == repository_id,
                RiskFinding.status == "open",
                RiskFinding.evidence["pr_number"].astext == str(pr_number),
            )
        ).scalar()
        or 0
    )


def run_pr_comment_job(
    repository_id: int,
    pr_number: int,
    *,
    require_enabled: bool = True,
    db: Session | None = None,
    client: GitHubClient | None = None,
    pr_files: list[ChangedFile] | None = None,
) -> dict | None:
    """Post (or refresh) Variorum's PR impact-briefing comment on GitHub.

    `require_enabled=True` (webhook path) skips repos that have not opted in;
    the manual endpoint passes `require_enabled=False` since posting is then the
    owner's explicit action. `db`, `client`, and `pr_files` are injectable for
    testing. Best-effort: returns the upsert result, or None if skipped/failed."""
    owns_session = db is None
    session = db or SessionLocal()
    try:
        return _run(session, repository_id, pr_number, require_enabled, client, pr_files)
    finally:
        if owns_session:
            session.close()


def _run(
    db: Session,
    repository_id: int,
    pr_number: int,
    require_enabled: bool,
    client: GitHubClient | None,
    pr_files: list[ChangedFile] | None,
) -> dict | None:
    repo = db.get(Repository, repository_id)
    if repo is None:
        logger.warning("pr comment: repository %s not found", repository_id)
        return None
    if require_enabled and not repo.pr_comments_enabled:
        return None

    installation = db.get(GitHubInstallation, repo.installation_id)
    if installation is None:
        logger.warning("pr comment: installation missing repo=%s", repo.full_name)
        return None

    try:
        gh = client or GitHubClient(GitHubAppAuth(get_settings()))
        if pr_files is None:
            pr_files = asyncio.run(
                gh.list_pull_request_files(
                    installation.installation_id, repo.full_name, pr_number
                )
            )
        paths = [f.path for f in pr_files]
        briefing = pr_impact_svc.build_briefing(db, repo.id, paths)
        body = pr_comment_svc.render_briefing_comment(
            briefing,
            repo_full_name=repo.full_name,
            default_branch=repo.default_branch,
            drift_open=_open_drift_count(db, repo.id, pr_number),
            risk_open=_open_risk_count(db, repo.id, pr_number),
        )
        result = asyncio.run(
            pr_comment_svc.upsert_pr_comment(
                gh, installation.installation_id, repo.full_name, pr_number, body
            )
        )
        logger.info(
            "pr comment %s repo=%s pr=%s", result.get("action"), repo.full_name, pr_number
        )
        return result
    except Exception as exc:  # noqa: BLE001 — never crash the worker on a comment
        logger.warning(
            "pr comment failed repo=%s pr=%s: %s", repo.full_name, pr_number, exc
        )
        return None
