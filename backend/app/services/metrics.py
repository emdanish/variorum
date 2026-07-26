from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisJob,
    CodeSymbol,
    DocCodeLink,
    Document,
    DriftFinding,
    FileChange,
    FindingStatus,
    RiskFinding,
)
from app.services import insights as insights_svc
from app.services.analysis.risk import is_source_path, is_test_path

_FIX_RE = re.compile(r"\b(fix|fixes|fixed|bug|bugfix|hotfix|patch|regression|revert)\b", re.I)

# Hotspot scoring weights (sum to 1.0). Documented so the score is explainable.
_W_CHURN = 0.35
_W_CHANGES = 0.25
_W_FIXES = 0.25
_W_NOCOVER = 0.15

_RISK_WEIGHTS = {"high": 15, "medium": 8, "low": 3, "info": 1}
# Health composite weights (renormalized over whichever subscores have data).
_HEALTH_WEIGHTS = {"documentation": 0.25, "coverage": 0.2, "risk": 0.3, "ownership": 0.25}


def is_fix_message(message: str | None) -> bool:
    return bool(message and _FIX_RE.search(message))


def _module(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "(root)"


def _stem(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name.split(".", 1)[0]


def _level(score: int) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def _bus_factor(contributions: list[float]) -> int:
    """Minimum number of top contributors whose cumulative share reaches 50%."""
    total = sum(contributions)
    if total <= 0:
        return 0
    running = 0.0
    for i, c in enumerate(sorted(contributions, reverse=True), start=1):
        running += c
        if running / total >= 0.5:
            return i
    return len(contributions)


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #


@dataclass
class FileChangeRecord:
    commit_sha: str
    path: str
    author: str | None
    additions: int
    deletions: int
    is_fix: bool
    occurred_at: datetime | None


def store_file_changes(db: Session, repository_id: int, records: list[FileChangeRecord]) -> int:
    """Idempotently upsert (commit, file) touches. Returns the number inserted."""
    existing = {
        (sha, path)
        for sha, path in db.execute(
            select(FileChange.commit_sha, FileChange.path).where(
                FileChange.repository_id == repository_id
            )
        ).all()
    }
    inserted = 0
    for r in records:
        if (r.commit_sha, r.path) in existing:
            continue
        db.add(
            FileChange(
                repository_id=repository_id,
                commit_sha=r.commit_sha,
                path=r.path,
                author=r.author,
                additions=r.additions,
                deletions=r.deletions,
                is_fix=r.is_fix,
                occurred_at=r.occurred_at,
            )
        )
        existing.add((r.commit_sha, r.path))
        inserted += 1
    if inserted:
        db.commit()
    return inserted


def has_file_changes(db: Session, repository_id: int) -> bool:
    return bool(
        db.scalar(
            select(func.count()).select_from(FileChange).where(
                FileChange.repository_id == repository_id
            )
        )
    )


# --------------------------------------------------------------------------- #
# Hotspots (behavioral code analysis)
# --------------------------------------------------------------------------- #


def _test_stems(db: Session, repository_id: int) -> set[str]:
    paths = db.execute(
        select(CodeSymbol.path).where(CodeSymbol.repository_id == repository_id).distinct()
    ).scalars()
    return {_stem(p) for p in paths if is_test_path(p)}


def compute_hotspots(db: Session, repository_id: int, *, limit: int = 20) -> list[dict]:
    rows = db.execute(
        select(
            FileChange.path,
            FileChange.author,
            FileChange.additions,
            FileChange.deletions,
            FileChange.is_fix,
        ).where(FileChange.repository_id == repository_id)
    ).all()

    agg: dict[str, dict] = {}
    for path, author, adds, dels, is_fix in rows:
        if not is_source_path(path):
            continue
        a = agg.setdefault(
            path, {"changes": 0, "churn": 0, "authors": set(), "fixes": 0}
        )
        a["changes"] += 1
        a["churn"] += (adds or 0) + (dels or 0)
        if author:
            a["authors"].add(author)
        if is_fix:
            a["fixes"] += 1
    if not agg:
        return []

    max_churn = max(a["churn"] for a in agg.values()) or 1
    max_changes = max(a["changes"] for a in agg.values()) or 1
    test_stems = _test_stems(db, repository_id)

    hotspots: list[dict] = []
    for path, a in agg.items():
        stem = _stem(path)
        # A source file is "covered" if its name appears inside a test file's
        # name (e.g. util.py -> test_util.py / util.test.ts).
        has_tests = bool(stem) and any(stem in ts for ts in test_stems)
        fix_ratio = a["fixes"] / a["changes"] if a["changes"] else 0.0
        raw = (
            _W_CHURN * (a["churn"] / max_churn)
            + _W_CHANGES * (a["changes"] / max_changes)
            + _W_FIXES * fix_ratio
            + _W_NOCOVER * (0.0 if has_tests else 1.0)
        )
        score = round(raw * 100)
        hotspots.append(
            {
                "path": path,
                "score": score,
                "level": _level(score),
                "changes": a["changes"],
                "churn": a["churn"],
                "authors": len(a["authors"]),
                "fixes": a["fixes"],
                "has_tests": has_tests,
            }
        )
    hotspots.sort(key=lambda h: (cast(int, h["score"]), cast(int, h["churn"])), reverse=True)
    return hotspots[:limit]


# --------------------------------------------------------------------------- #
# Ownership / bus factor
# --------------------------------------------------------------------------- #


def compute_ownership(db: Session, repository_id: int) -> dict:
    rows = db.execute(
        select(
            FileChange.path,
            FileChange.author,
            FileChange.additions,
            FileChange.deletions,
        ).where(FileChange.repository_id == repository_id)
    ).all()

    modules: dict[str, dict[str, float]] = {}
    for path, author, adds, dels in rows:
        if not is_source_path(path):
            continue
        contrib = (adds or 0) + (dels or 0) or 1  # a touch counts even with 0 lines
        modules.setdefault(_module(path), {})
        modules[_module(path)][author or "unknown"] = (
            modules[_module(path)].get(author or "unknown", 0) + contrib
        )

    result: list[dict] = []
    single_owner = 0
    for module, authors in sorted(modules.items()):
        total = sum(authors.values())
        primary, primary_contrib = max(authors.items(), key=lambda kv: kv[1])
        primary_share = primary_contrib / total if total else 0.0
        bus = _bus_factor(list(authors.values()))
        # Flag a module as single-owner only when knowledge is genuinely
        # concentrated: one author, or one author owns 80%+ of the changes.
        is_single = len(authors) == 1 or primary_share >= 0.8
        if is_single:
            single_owner += 1
        result.append(
            {
                "module": module,
                "author_count": len(authors),
                "primary_owner": primary,
                "primary_share": round(primary_share, 3),
                "bus_factor": bus,
                "single_owner": is_single,
            }
        )
    result.sort(
        key=lambda m: (cast(bool, m["single_owner"]), -cast(float, m["primary_share"])),
        reverse=True,
    )
    return {
        "modules": result,
        "module_count": len(result),
        "single_owner_modules": single_owner,
    }


# --------------------------------------------------------------------------- #
# Documentation coverage
# --------------------------------------------------------------------------- #


def compute_doc_coverage(db: Session, repository_id: int) -> dict:
    source_paths = {
        p
        for p in db.execute(
            select(CodeSymbol.path).where(CodeSymbol.repository_id == repository_id).distinct()
        ).scalars()
        if is_source_path(p)
    }
    if not source_paths:
        return {"overall_pct": 0.0, "documented": 0, "total": 0, "modules": []}

    # A source path is "documented" if a doc↔code link (scoped to this repo via
    # its document) references it, either by explicit path or via a symbol.
    links = db.execute(
        select(DocCodeLink.path, CodeSymbol.path)
        .join(Document, DocCodeLink.document_id == Document.id)
        .join(CodeSymbol, DocCodeLink.symbol_id == CodeSymbol.id, isouter=True)
        .where(Document.repository_id == repository_id)
    ).all()
    documented: set[str] = set()
    for link_path, symbol_path in links:
        if link_path:
            documented.add(link_path)
        if symbol_path:
            documented.add(symbol_path)
    documented &= source_paths

    modules: dict[str, dict[str, int]] = {}
    for p in source_paths:
        m = modules.setdefault(_module(p), {"documented": 0, "total": 0})
        m["total"] += 1
        if p in documented:
            m["documented"] += 1

    module_list = [
        {
            "module": module,
            "documented": v["documented"],
            "total": v["total"],
            "pct": round(100 * v["documented"] / v["total"], 1) if v["total"] else 0.0,
        }
        for module, v in sorted(modules.items())
    ]
    module_list.sort(key=lambda m: cast(float, m["pct"]))
    total = len(source_paths)
    return {
        "overall_pct": round(100 * len(documented) / total, 1) if total else 0.0,
        "documented": len(documented),
        "total": total,
        "modules": module_list,
    }


# --------------------------------------------------------------------------- #
# Composite health score
# --------------------------------------------------------------------------- #


def _documentation_subscore(db: Session, repository_id: int) -> int | None:
    rows = db.execute(
        select(DriftFinding.severity, DriftFinding.status)
        .join(AnalysisJob, DriftFinding.analysis_job_id == AnalysisJob.id)
        .where(AnalysisJob.repository_id == repository_id)
    ).all()
    if not rows:
        return None
    open_by_severity: dict[str, int] = {}
    for severity, status in rows:
        if status == FindingStatus.detected:
            key = severity.value
            open_by_severity[key] = open_by_severity.get(key, 0) + 1
    return insights_svc.doc_health_score(open_by_severity)


def _risk_subscore(db: Session, repository_id: int) -> int | None:
    rows = db.execute(
        select(RiskFinding.risk_level, RiskFinding.status)
        .join(AnalysisJob, RiskFinding.analysis_job_id == AnalysisJob.id)
        .where(AnalysisJob.repository_id == repository_id)
    ).all()
    if not rows:
        return None
    penalty = sum(
        _RISK_WEIGHTS.get(level.value, 0) for level, status in rows if status != "dismissed"
    )
    return max(0, 100 - penalty)


def compute_health(db: Session, repository_id: int) -> dict:
    """Composite 0–100 knowledge-health score, averaged over whichever
    subscores have data (documentation, coverage, risk, ownership)."""
    coverage = compute_doc_coverage(db, repository_id)
    ownership = compute_ownership(db, repository_id)

    subscores: dict[str, int] = {}
    doc = _documentation_subscore(db, repository_id)
    if doc is not None:
        subscores["documentation"] = doc
    if coverage["total"]:
        subscores["coverage"] = round(coverage["overall_pct"])
    risk = _risk_subscore(db, repository_id)
    if risk is not None:
        subscores["risk"] = risk
    if ownership["module_count"]:
        subscores["ownership"] = round(
            100 * (1 - ownership["single_owner_modules"] / ownership["module_count"])
        )

    if subscores:
        weight = sum(_HEALTH_WEIGHTS[k] for k in subscores)
        score = round(sum(subscores[k] * _HEALTH_WEIGHTS[k] for k in subscores) / weight)
    else:
        score = 0
    return {
        "score": score,
        "level": _level(score),
        "subscores": subscores,
        "single_owner_modules": ownership["single_owner_modules"],
        "module_count": ownership["module_count"],
        "doc_coverage_pct": coverage["overall_pct"],
    }
