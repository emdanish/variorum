from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingService
from app.ai.service import AIService
from app.core.logging import get_logger
from app.models import AnalysisJob, DocCodeLink, Document, RiskFinding
from app.services import metrics as metrics_svc
from app.services import qa as qa_svc

logger = get_logger("variorum.change_briefing")

MAX_LOCATIONS = 6

SYSTEM_PROMPT = (
    "You are Variorum's change-planning assistant. A developer is about to make a "
    "change. Using ONLY the structured context provided, write a short briefing "
    "(2-4 sentences) on what they should know before they start and the biggest "
    "risk to watch. Be concrete and practical; name files/owners when relevant. "
    "Do not invent facts. Plain prose, no preamble."
)


def _module(path: str) -> str:
    return path.split("/", 1)[0] if "/" in path else "(root)"


def _blob_url(repo_full_name: str | None, branch: str, path: str, line: int | None) -> str | None:
    if not repo_full_name or not path:
        return None
    anchor = f"#L{line}" if line else ""
    return f"https://github.com/{repo_full_name}/blob/{branch}/{path}{anchor}"


def build_change_briefing(
    db: Session,
    repository_id: int,
    query: str,
    *,
    embedder: EmbeddingService | None = None,
    repo_full_name: str | None = None,
    default_branch: str = "main",
) -> dict:
    """Compose a pre-work briefing for an intended change: where the code lives,
    how risky it is to touch, who owns it, why it's built that way, which docs
    will drift, and where tests are missing. Deterministic over the DB — reliable
    without AI (the AI TL;DR is layered on separately)."""
    code_hits = qa_svc.retrieve_code(
        db, repository_id, query, k=MAX_LOCATIONS, embedder=embedder
    )
    target_paths = list(dict.fromkeys(s.path for s in code_hits))  # unique, order-preserving

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

    locations: list[dict] = []
    for s in code_hits:
        h = hmap.get(s.path)
        locations.append(
            {
                "path": s.path,
                "name": s.name,
                "kind": s.kind,
                "url": _blob_url(repo_full_name, default_branch, s.path, s.start_line),
                "hotspot_score": h["score"] if h else None,
                "hotspot_level": h["level"] if h else None,
                "has_tests": h["has_tests"] if h else None,
                "module": _module(s.path),
                "risk_findings": risk_counts.get(s.path, 0),
            }
        )

    # Who to ask — owners of the modules involved, single-owner (bus-factor 1)
    # surfaced first as the people to loop in before touching their area.
    experts: list[dict] = []
    for module in dict.fromkeys(_module(p) for p in target_paths):
        own = module_map.get(module)
        if own is None:
            continue
        experts.append(
            {
                "module": module,
                "primary_owner": own["primary_owner"],
                "bus_factor": own["bus_factor"],
                "single_owner": bool(own["single_owner"]),
            }
        )
    experts.sort(key=lambda e: (not e["single_owner"],))

    # Why it's this way — decisions + history relevant to the intent.
    decisions = [
        {"id": d.id, "title": d.title, "summary": d.summary, "decided_at": d.decided_at}
        for d in qa_svc.retrieve_decisions(db, repository_id, query, embedder=embedder)
    ]
    history = [
        {"kind": e.kind.value, "source_ref": e.source_ref, "title": e.title, "url": e.url}
        for e in qa_svc.retrieve(db, repository_id, query, k=4, embedder=embedder)
    ]

    # Docs that will drift — documentation linked to the target files/symbols.
    docs_to_update: list[dict] = []
    if target_paths:
        symbol_ids = [s.id for s in code_hits]
        doc_rows = db.execute(
            select(Document.path, Document.title)
            .join(DocCodeLink, DocCodeLink.document_id == Document.id)
            .where(
                Document.repository_id == repository_id,
                (DocCodeLink.path.in_(target_paths))
                | (DocCodeLink.symbol_id.in_(symbol_ids)),
            )
            .distinct()
        ).all()
        docs_to_update = [
            {
                "path": path,
                "title": title,
                "url": _blob_url(repo_full_name, default_branch, path, None),
            }
            for path, title in doc_rows
        ]

    test_gaps = [loc["path"] for loc in locations if loc["has_tests"] is False]

    return {
        "query": query,
        "summary": None,
        "locations": locations,
        "experts": experts,
        "decisions": decisions,
        "history": history,
        "docs_to_update": docs_to_update,
        "test_gaps": list(dict.fromkeys(test_gaps)),
        "provider": None,
    }


def _summary_prompt(briefing: dict) -> str:
    lines = [f"Intended change: {briefing['query']}", ""]
    if briefing["locations"]:
        lines.append("Relevant code:")
        for loc in briefing["locations"][:6]:
            risk = loc["hotspot_level"] or "unknown"
            tests = "no tests" if loc["has_tests"] is False else "has tests"
            lines.append(f"- {loc['name']} in {loc['path']} (risk: {risk}, {tests})")
    if briefing["experts"]:
        owners = ", ".join(
            f"{e['module']} → {e['primary_owner']}"
            + (" (SOLE OWNER)" if e["single_owner"] else "")
            for e in briefing["experts"][:5]
        )
        lines.append(f"Owners: {owners}")
    if briefing["decisions"]:
        lines.append("Relevant decisions:")
        lines.extend(f"- {d['title']}" for d in briefing["decisions"][:3])
    if briefing["docs_to_update"]:
        lines.append(
            "Docs likely to drift: " + ", ".join(d["path"] for d in briefing["docs_to_update"][:5])
        )
    if briefing["test_gaps"]:
        lines.append("Untested files being touched: " + ", ".join(briefing["test_gaps"][:5]))
    return "\n".join(lines)


async def summarize(ai: AIService, briefing: dict) -> tuple[str | None, str | None]:
    """Best-effort AI TL;DR over the structured briefing. Returns (summary,
    provider); (None, None) if AI is unavailable or fails — the structured
    briefing stands on its own."""
    if not ai.available:
        return None, None
    try:
        result = await ai.complete(_summary_prompt(briefing), system=SYSTEM_PROMPT)
    except Exception as exc:  # noqa: BLE001 — the TL;DR is optional
        logger.warning("change-briefing summary failed: %s", exc)
        return None, None
    text = (result.text or "").strip()
    return (text or None), (result.provider if text else None)
