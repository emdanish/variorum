from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.models import DecisionEntry, KnowledgeEntry, KnowledgeKind

# Prefer PRs and issues (they carry rationale) over bare commits, and keep the
# context compact.
_MAX_CONTEXT = 40
_MAX_BODY = 320
_MAX_DECISIONS = 12
_KIND_PRIORITY = {
    KnowledgeKind.pull_request: 0,
    KnowledgeKind.issue: 1,
    KnowledgeKind.review: 2,
    KnowledgeKind.commit: 3,
}

SYSTEM_PROMPT = (
    "You are Variorum's engineering historian. From the numbered history entries "
    "below (pull requests, issues, commits), extract the SIGNIFICANT engineering "
    "decisions — architectural choices, tradeoffs, notable workarounds, or "
    "direction changes. Ignore routine changes.\n"
    "Rules:\n"
    "- Base every decision only on the provided entries; never invent history.\n"
    "- Each decision must cite the entry numbers it is drawn from.\n"
    "- 'summary' states what was decided AND why, in 1-3 sentences.\n"
    f"- Return at most {_MAX_DECISIONS}, most significant first.\n"
    'Respond in strict JSON: {"decisions": [{"title": string, "summary": string, '
    '"cited": [int, ...]}]}'
)


def gather_entries(db: Session, repository_id: int) -> list[KnowledgeEntry]:
    entries = list(
        db.execute(
            select(KnowledgeEntry).where(KnowledgeEntry.repository_id == repository_id)
        )
        .scalars()
        .all()
    )
    entries.sort(
        key=lambda e: (
            _KIND_PRIORITY.get(e.kind, 9),
            -(e.occurred_at.timestamp() if e.occurred_at else 0.0),
        )
    )
    return entries[:_MAX_CONTEXT]


def build_prompt(entries: list[KnowledgeEntry]) -> str:
    lines = []
    for i, e in enumerate(entries, start=1):
        date = e.occurred_at.date().isoformat() if e.occurred_at else "n/a"
        body = (e.body or "").strip().replace("\n", " ")[:_MAX_BODY]
        lines.append(f"[{i}] {e.kind.value} {e.source_ref} ({date}) — {e.title or ''}\n{body}")
    return "History entries:\n" + "\n\n".join(lines)


def _parse(data: dict, entries: list[KnowledgeEntry]) -> list[dict]:
    raw = data.get("decisions")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw[:_MAX_DECISIONS]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        summary = str(item.get("summary", "")).strip()
        if not title or not summary:
            continue
        cited_idx = {
            n for n in (item.get("cited") or []) if isinstance(n, int) and 1 <= n <= len(entries)
        }
        cited = [entries[n - 1] for n in sorted(cited_idx)]
        sources = [
            {"ref": e.source_ref, "kind": e.kind.value, "url": e.url} for e in cited
        ]
        dates = [e.occurred_at for e in cited if e.occurred_at]
        decided_at = min(dates) if dates else None
        out.append(
            {"title": title[:300], "summary": summary[:2000], "sources": sources,
             "decided_at": decided_at}
        )
    return out


async def generate_decisions(
    ai: AIService, entries: list[KnowledgeEntry]
) -> tuple[list[dict], str | None, str | None]:
    data, result = await ai.complete_structured(
        build_prompt(entries), system=SYSTEM_PROMPT, purpose="decision_timeline"
    )
    return _parse(data, entries), result.provider, result.model


def replace_decisions(
    db: Session,
    repository_id: int,
    decisions: list[dict],
    *,
    provider: str | None,
    model: str | None,
) -> int:
    """Replace the repository's decision timeline with a freshly synthesized set."""
    db.query(DecisionEntry).filter(DecisionEntry.repository_id == repository_id).delete()
    for d in decisions:
        db.add(
            DecisionEntry(
                repository_id=repository_id,
                title=d["title"],
                summary=d["summary"],
                sources=d["sources"],
                decided_at=d["decided_at"],
                provider=provider,
                model=model,
            )
        )
    db.commit()
    return len(decisions)


def list_decisions(db: Session, repository_id: int) -> list[DecisionEntry]:
    return list(
        db.execute(
            select(DecisionEntry)
            .where(DecisionEntry.repository_id == repository_id)
            .order_by(DecisionEntry.decided_at.desc().nullslast(), DecisionEntry.id.desc())
        )
        .scalars()
        .all()
    )
