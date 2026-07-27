from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    AnalysisJob,
    DriftFinding,
    FindingStatus,
    GitHubInstallation,
    IndexingStatus,
    MetricSnapshot,
    Repository,
    RiskFinding,
)
from app.services import metrics as metrics_svc

# Alert thresholds.
HEALTH_DROP = 10  # points of health-score regression that raise an alert
HEALTH_DROP_CRITICAL = 20
# Minimum spacing between periodic (scheduler-driven) snapshots per repo.
PERIODIC_MIN_AGE = timedelta(hours=12)


def _open_drift(db: Session, repository_id: int) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(DriftFinding)
            .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
            .where(
                AnalysisJob.repository_id == repository_id,
                DriftFinding.status == FindingStatus.detected,
            )
        ).scalar()
        or 0
    )


def _open_risk(db: Session, repository_id: int) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(RiskFinding)
            .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
            .where(AnalysisJob.repository_id == repository_id, RiskFinding.status == "open")
        ).scalar()
        or 0
    )


def compute_metrics(db: Session, repository_id: int) -> dict:
    """Current knowledge-health metrics for a repository — the fields captured in
    each snapshot. Pure read over existing metric services."""
    health = metrics_svc.compute_health(db, repository_id)
    hotspots = metrics_svc.hotspot_map(db, repository_id).values()
    return {
        "health_score": health["score"],
        "doc_coverage_pct": round(health["doc_coverage_pct"], 2),
        "single_owner_modules": health["single_owner_modules"],
        "module_count": health["module_count"],
        "critical_hotspots": sum(1 for h in hotspots if h["level"] == "critical"),
        "high_hotspots": sum(1 for h in hotspots if h["level"] == "high"),
        "drift_open": _open_drift(db, repository_id),
        "risk_open": _open_risk(db, repository_id),
    }


def latest_snapshot(db: Session, repository_id: int) -> MetricSnapshot | None:
    return db.execute(
        select(MetricSnapshot)
        .where(MetricSnapshot.repository_id == repository_id)
        .order_by(MetricSnapshot.captured_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def history(db: Session, repository_id: int, *, limit: int = 60) -> list[MetricSnapshot]:
    rows = (
        db.execute(
            select(MetricSnapshot)
            .where(MetricSnapshot.repository_id == repository_id)
            .order_by(MetricSnapshot.captured_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(reversed(rows))  # oldest → newest for charting


def detect_alerts(prev: MetricSnapshot, curr: MetricSnapshot) -> list[dict]:
    """Compare two consecutive snapshots and return alert descriptors. Consecutive
    comparison means a one-off regression raises exactly one alert."""
    out: list[dict] = []
    drop = prev.health_score - curr.health_score
    if prev.health_score > 0 and drop >= HEALTH_DROP:
        out.append(
            {
                "kind": "health_drop",
                "severity": "critical" if drop >= HEALTH_DROP_CRITICAL else "warning",
                "title": (
                    f"Health dropped {drop} points "
                    f"({prev.health_score} → {curr.health_score})"
                ),
                "detail": "Knowledge-health score regressed since the last snapshot.",
            }
        )
    if curr.critical_hotspots > prev.critical_hotspots:
        added = curr.critical_hotspots - prev.critical_hotspots
        out.append(
            {
                "kind": "new_critical_hotspot",
                "severity": "critical",
                "title": f"{added} new critical hotspot(s)",
                "detail": (
                    f"Critical hotspots rose from {prev.critical_hotspots} to "
                    f"{curr.critical_hotspots}."
                ),
            }
        )
    if curr.single_owner_modules > prev.single_owner_modules:
        out.append(
            {
                "kind": "single_owner_increase",
                "severity": "warning",
                "title": (
                    f"Single-owner modules rose to {curr.single_owner_modules}"
                ),
                "detail": (
                    f"Bus-factor risk increased ({prev.single_owner_modules} → "
                    f"{curr.single_owner_modules} modules with one owner)."
                ),
            }
        )
    return out


def capture(
    db: Session, repository_id: int, now: datetime
) -> tuple[MetricSnapshot, list[Alert]]:
    """Record a snapshot and raise alerts for regressions vs. the previous one.
    Commits. Returns (snapshot, new_alerts)."""
    prev = latest_snapshot(db, repository_id)
    m = compute_metrics(db, repository_id)
    snapshot = MetricSnapshot(repository_id=repository_id, captured_at=now, **m)
    db.add(snapshot)
    db.flush()

    alerts: list[Alert] = []
    if prev is not None:
        for a in detect_alerts(prev, snapshot):
            alert = Alert(repository_id=repository_id, **a)
            db.add(alert)
            alerts.append(alert)
    db.commit()
    return snapshot, alerts


def capture_stale(db: Session, now: datetime) -> int:
    """Snapshot every indexed repository whose latest snapshot is older than
    PERIODIC_MIN_AGE (or has none). Driven by the scheduler so trends and alerts
    advance even without an ingest. Best-effort per repo. Returns count captured."""
    repos = (
        db.execute(
            select(Repository.id).where(Repository.indexing_status == IndexingStatus.indexed)
        )
        .scalars()
        .all()
    )
    captured = 0
    for repo_id in repos:
        latest = latest_snapshot(db, repo_id)
        if latest is not None and (now - latest.captured_at) < PERIODIC_MIN_AGE:
            continue
        try:
            capture(db, repo_id, now)
            captured += 1
        except Exception:  # noqa: BLE001 — isolate per-repo failures
            db.rollback()
    return captured


def list_alerts(
    db: Session, repository_id: int, *, include_acknowledged: bool = False, limit: int = 50
) -> list[Alert]:
    stmt = select(Alert).where(Alert.repository_id == repository_id)
    if not include_acknowledged:
        stmt = stmt.where(Alert.acknowledged_at.is_(None))
    stmt = stmt.order_by(Alert.created_at.desc()).limit(limit)
    return list(db.execute(stmt).scalars().all())


def acknowledge(db: Session, repository_id: int, alert_id: int, now: datetime) -> bool:
    alert = db.execute(
        select(Alert).where(Alert.id == alert_id, Alert.repository_id == repository_id)
    ).scalar_one_or_none()
    if alert is None:
        return False
    if alert.acknowledged_at is None:
        alert.acknowledged_at = now
        db.commit()
    return True


def list_alerts_for_user(db: Session, user_id: int, *, limit: int = 50) -> list[Alert]:
    """Unacknowledged alerts across every repository the user owns — the feed for
    the in-app notification center."""
    return list(
        db.execute(
            select(Alert)
            .join(Repository, Alert.repository_id == Repository.id)
            .join(GitHubInstallation, Repository.installation_id == GitHubInstallation.id)
            .where(
                GitHubInstallation.owner_user_id == user_id,
                Alert.acknowledged_at.is_(None),
            )
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
