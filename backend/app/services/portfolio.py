from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisJob,
    DriftFinding,
    DriftSeverity,
    FindingStatus,
    GitHubInstallation,
    Repository,
    RiskFinding,
)
from app.services import metrics as metrics_svc


def _owned_repos(db: Session, user_id: int) -> list[Repository]:
    return list(
        db.execute(
            select(Repository)
            .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
            .where(GitHubInstallation.owner_user_id == user_id)
            .order_by(Repository.full_name)
        )
        .scalars()
        .all()
    )


def build_portfolio(db: Session, user_id: int) -> dict:
    """Org-wide health view: every owned repository ranked worst-health first,
    plus a portfolio summary for leadership."""
    repos = _owned_repos(db, user_id)
    items: list[dict] = []
    for repo in repos:
        health = metrics_svc.compute_health(db, repo.id)
        hotspots = metrics_svc.compute_hotspots(db, repo.id, limit=1)
        drift_open = int(
            db.scalar(
                select(func.count())
                .select_from(DriftFinding)
                .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
                .where(
                    AnalysisJob.repository_id == repo.id,
                    DriftFinding.status == FindingStatus.detected,
                )
            )
            or 0
        )
        risk_high = int(
            db.scalar(
                select(func.count())
                .select_from(RiskFinding)
                .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
                .where(
                    AnalysisJob.repository_id == repo.id,
                    RiskFinding.risk_level == DriftSeverity.high,
                )
            )
            or 0
        )
        items.append(
            {
                "repository_id": repo.id,
                "full_name": repo.full_name,
                "indexing_status": repo.indexing_status.value,
                "health_score": health["score"],
                "health_level": health["level"],
                "doc_coverage_pct": health["doc_coverage_pct"],
                "single_owner_modules": health["single_owner_modules"],
                "drift_open": drift_open,
                "risk_high": risk_high,
                "top_hotspot": hotspots[0]["path"] if hotspots else None,
            }
        )

    items.sort(key=lambda r: r["health_score"])  # worst health first
    avg_health = round(sum(r["health_score"] for r in items) / len(items)) if items else 0
    return {
        "repos": items,
        "summary": {
            "repo_count": len(items),
            "avg_health": avg_health,
            "at_risk": sum(1 for r in items if r["health_score"] < 50),
            "total_single_owner": sum(r["single_owner_modules"] for r in items),
        },
    }
