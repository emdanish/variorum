from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import (
    AnalysisJob,
    DriftFinding,
    DriftSeverity,
    GitHubInstallation,
    IndexingStatus,
    KnowledgeEntry,
    Repository,
    RiskFinding,
    User,
)
from app.schemas import TeamInsights

router = APIRouter(prefix="/teams", tags=["teams"])


def _group_count(db: Session, stmt) -> dict[int, int]:
    return dict(db.execute(stmt).all())


@router.get("", response_model=list[TeamInsights])
def list_teams(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TeamInsights]:
    """Per-team rollup, where a team is a GitHub App installation (an org or
    account). Aggregates repositories, findings, risk, and knowledge across all
    repositories the installation owns."""
    installations = (
        db.execute(
            select(GitHubInstallation)
            .where(GitHubInstallation.owner_user_id == user.id)
            .order_by(GitHubInstallation.account_login)
        )
        .scalars()
        .all()
    )
    if not installations:
        return []

    inst_ids = [inst.id for inst in installations]

    repo_rows = db.execute(
        select(
            Repository.installation_id,
            func.count(Repository.id),
            func.coalesce(
                func.sum(
                    case((Repository.indexing_status == IndexingStatus.indexed, 1), else_=0)
                ),
                0,
            ),
        )
        .where(Repository.installation_id.in_(inst_ids))
        .group_by(Repository.installation_id)
    ).all()
    repo_counts = {r[0]: r[1] for r in repo_rows}
    indexed_counts = {r[0]: r[2] for r in repo_rows}

    drift_counts = _group_count(
        db,
        select(Repository.installation_id, func.count(DriftFinding.id))
        .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
        .join(Repository, AnalysisJob.repository_id == Repository.id)
        .where(Repository.installation_id.in_(inst_ids))
        .group_by(Repository.installation_id),
    )
    risk_counts = _group_count(
        db,
        select(Repository.installation_id, func.count(RiskFinding.id))
        .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
        .join(Repository, AnalysisJob.repository_id == Repository.id)
        .where(Repository.installation_id.in_(inst_ids))
        .group_by(Repository.installation_id),
    )
    high_risk_counts = _group_count(
        db,
        select(Repository.installation_id, func.count(RiskFinding.id))
        .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
        .join(Repository, AnalysisJob.repository_id == Repository.id)
        .where(
            Repository.installation_id.in_(inst_ids),
            RiskFinding.risk_level == DriftSeverity.high,
        )
        .group_by(Repository.installation_id),
    )
    knowledge_counts = _group_count(
        db,
        select(Repository.installation_id, func.count(KnowledgeEntry.id))
        .join(Repository, KnowledgeEntry.repository_id == Repository.id)
        .where(Repository.installation_id.in_(inst_ids))
        .group_by(Repository.installation_id),
    )
    activity_rows = db.execute(
        select(Repository.installation_id, func.max(AnalysisJob.created_at))
        .join(Repository, AnalysisJob.repository_id == Repository.id)
        .where(Repository.installation_id.in_(inst_ids))
        .group_by(Repository.installation_id)
    ).all()
    last_activity = {r[0]: r[1] for r in activity_rows}

    return [
        TeamInsights(
            id=inst.id,
            installation_id=inst.installation_id,
            account_login=inst.account_login,
            account_type=inst.account_type,
            suspended=inst.suspended_at is not None,
            repo_count=repo_counts.get(inst.id, 0),
            indexed_count=int(indexed_counts.get(inst.id, 0)),
            drift_total=drift_counts.get(inst.id, 0),
            risk_total=risk_counts.get(inst.id, 0),
            high_risk=high_risk_counts.get(inst.id, 0),
            knowledge_total=knowledge_counts.get(inst.id, 0),
            last_activity_at=last_activity.get(inst.id),
        )
        for inst in installations
    ]
