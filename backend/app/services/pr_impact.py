from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AnalysisJob, RiskFinding
from app.services import metrics as metrics_svc
from app.services.analysis.risk import is_source_path


def _module(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "(root)"


def build_briefing(db: Session, repository_id: int, paths: list[str]) -> dict:
    """Compose pre-merge intelligence for a PR's changed files: each file's
    behavioral hotspot score, module owner / bus factor, and prior test-risk
    findings. Pure over the DB — the caller supplies the PR's changed paths."""
    source_paths = [p for p in paths if is_source_path(p)]

    hmap = metrics_svc.hotspot_map(db, repository_id)
    ownership = metrics_svc.compute_ownership(db, repository_id)
    module_map = {m["module"]: m for m in ownership["modules"]}
    risk_rows = db.execute(
        select(RiskFinding.path, func.count())
        .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
        .where(AnalysisJob.repository_id == repository_id)
        .group_by(RiskFinding.path)
    ).all()
    risk_counts: dict[str, int] = {row[0]: row[1] for row in risk_rows}

    files: list[dict] = []
    for path in source_paths:
        module = _module(path)
        h = hmap.get(path)
        own = module_map.get(module)
        files.append(
            {
                "path": path,
                "hotspot_score": h["score"] if h else None,
                "hotspot_level": h["level"] if h else None,
                "has_tests": h["has_tests"] if h else None,
                "module": module,
                "primary_owner": own["primary_owner"] if own else None,
                "bus_factor": own["bus_factor"] if own else None,
                "single_owner": bool(own["single_owner"]) if own else False,
                "risk_findings": risk_counts.get(path, 0),
            }
        )
    files.sort(
        key=lambda f: f["hotspot_score"] if f["hotspot_score"] is not None else -1,
        reverse=True,
    )

    high_risk = [f for f in files if f["hotspot_level"] in ("critical", "high")]
    single_owner = [f for f in files if f["single_owner"]]
    untested = [f for f in files if f["has_tests"] is False]
    return {
        "files": files,
        "summary": {
            "files_analyzed": len(files),
            "high_risk_files": len(high_risk),
            "single_owner_files": len(single_owner),
            "untested_files": len(untested),
            "top_file": files[0]["path"] if files else None,
        },
    }
