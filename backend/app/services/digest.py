from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisJob,
    DecisionEntry,
    DriftFinding,
    KnowledgeEntry,
    RiskFinding,
)
from app.services import metrics as metrics_svc


def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def build_digest(db: Session, repository_id: int, *, days: int = 7) -> dict:
    """A trailing-window recap of what changed: new findings, knowledge added,
    decisions, emerging hotspots, and the current health snapshot."""
    window = datetime.now(UTC) - timedelta(days=days)

    new_drift = _count(
        db,
        select(func.count())
        .select_from(DriftFinding)
        .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
        .where(AnalysisJob.repository_id == repository_id, DriftFinding.created_at >= window),
    )
    new_risk = _count(
        db,
        select(func.count())
        .select_from(RiskFinding)
        .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
        .where(AnalysisJob.repository_id == repository_id, RiskFinding.created_at >= window),
    )
    new_knowledge = _count(
        db,
        select(func.count())
        .select_from(KnowledgeEntry)
        .where(
            KnowledgeEntry.repository_id == repository_id, KnowledgeEntry.created_at >= window
        ),
    )
    decisions_total = _count(
        db,
        select(func.count())
        .select_from(DecisionEntry)
        .where(DecisionEntry.repository_id == repository_id),
    )

    recent_knowledge = (
        db.execute(
            select(KnowledgeEntry)
            .where(
                KnowledgeEntry.repository_id == repository_id,
                KnowledgeEntry.created_at >= window,
            )
            .order_by(KnowledgeEntry.created_at.desc())
            .limit(5)
        )
        .scalars()
        .all()
    )

    health = metrics_svc.compute_health(db, repository_id)
    hotspots = metrics_svc.compute_hotspots(db, repository_id, limit=3)

    return {
        "days": days,
        "new_drift": new_drift,
        "new_risk": new_risk,
        "new_knowledge": new_knowledge,
        "decisions_total": decisions_total,
        "health_score": health["score"],
        "health_level": health["level"],
        "single_owner_modules": health["single_owner_modules"],
        "top_hotspots": hotspots,
        "recent_knowledge": [
            {"kind": k.kind.value, "source_ref": k.source_ref, "title": k.title, "url": k.url}
            for k in recent_knowledge
        ],
        "generated_at": datetime.now(UTC),
    }
