from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.models import CodeSymbol, Document, KnowledgeEntry, Repository, RepositoryGuide

# Bounds keep the prompt compact and the output predictable.
_MAX_MODULES = 12
_MAX_DOCS = 20
_MAX_HISTORY = 15
_MAX_AREAS = 8
_MAX_LIST = 8

SYSTEM_PROMPT = (
    "You are Variorum's repository-orientation assistant. Using ONLY the facts "
    "below (code structure, documentation, and engineering history), write a "
    "concise onboarding guide for an engineer new to this repository.\n"
    "Rules:\n"
    "- Ground every statement in the provided facts; never invent files, APIs, or "
    "history.\n"
    "- For decisions, cite the source (commit/PR/issue reference) you drew from.\n"
    "- Prefer concrete paths and module names over vague description.\n"
    "Respond in strict JSON with this shape:\n"
    "{\n"
    '  "summary": string,  // one paragraph: what this repository is and does\n'
    '  "key_areas": [{"name": string, "description": string, "paths": [string]}],\n'
    '  "getting_started": [string],  // where a newcomer should start\n'
    '  "decisions": [{"title": string, "detail": string, "source": string}],\n'
    '  "conventions": [string]\n'
    "}"
)


def _top_level_dir(path: str) -> str:
    head = path.split("/", 1)[0]
    return head if "/" in path else "(root)"


def build_context(db: Session, repo: Repository) -> str:
    symbols = (
        db.execute(
            select(CodeSymbol.path, CodeSymbol.language, CodeSymbol.kind).where(
                CodeSymbol.repository_id == repo.id
            )
        )
        .all()
    )
    symbol_count = len(symbols)
    languages = Counter(s.language for s in symbols if s.language)
    modules = Counter(_top_level_dir(s.path) for s in symbols)

    documents = (
        db.execute(
            select(Document.path, Document.title)
            .where(Document.repository_id == repo.id)
            .order_by(Document.path)
            .limit(_MAX_DOCS)
        )
        .all()
    )
    document_count = db.scalar(
        select(func.count()).select_from(Document).where(Document.repository_id == repo.id)
    )

    history = (
        db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.repository_id == repo.id)
            .order_by(KnowledgeEntry.occurred_at.desc().nullslast())
            .limit(_MAX_HISTORY)
        )
        .scalars()
        .all()
    )

    lines: list[str] = [
        f"Repository: {repo.full_name}",
        f"Default branch: {repo.default_branch}",
        f"Indexed symbols: {symbol_count} | Documents: {document_count or 0} | "
        f"History entries: {len(history)}",
    ]
    if languages:
        top_langs = ", ".join(f"{lang} ({n})" for lang, n in languages.most_common(6))
        lines.append(f"Languages: {top_langs}")
    if modules:
        top_mods = ", ".join(
            f"{name} ({n} symbols)" for name, n in modules.most_common(_MAX_MODULES)
        )
        lines.append(f"Top-level modules: {top_mods}")
    if documents:
        lines.append("Documentation files:")
        lines.extend(f"  - {d.path}{f' — {d.title}' if d.title else ''}" for d in documents)
    if history:
        lines.append("Recent engineering history:")
        for e in history:
            title = (e.title or "").strip().replace("\n", " ")
            lines.append(f"  - [{e.kind.value} {e.source_ref}] {title[:160]}")
    return "\n".join(lines)


def _as_str_list(value: object, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:limit]


def _parse_areas(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    areas: list[dict] = []
    for item in value[:_MAX_AREAS]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        areas.append(
            {
                "name": name[:120],
                "description": str(item.get("description", "")).strip()[:600],
                "paths": _as_str_list(item.get("paths"), 6),
            }
        )
    return areas


def _parse_decisions(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []
    decisions: list[dict] = []
    for item in value[:_MAX_LIST]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        decisions.append(
            {
                "title": title[:160],
                "detail": str(item.get("detail", "")).strip()[:600],
                "source": str(item.get("source", "")).strip()[:120],
            }
        )
    return decisions


def parse_guide(data: dict) -> tuple[str, dict]:
    """Coerce the model's JSON into the stored guide shape, defensively."""
    summary = str(data.get("summary", "")).strip()
    content = {
        "key_areas": _parse_areas(data.get("key_areas")),
        "getting_started": _as_str_list(data.get("getting_started"), _MAX_LIST),
        "decisions": _parse_decisions(data.get("decisions")),
        "conventions": _as_str_list(data.get("conventions"), _MAX_LIST),
    }
    return summary, content


async def generate_orientation(
    ai: AIService, context: str
) -> tuple[str, dict, str | None, str | None]:
    data, result = await ai.complete_structured(
        f"Facts:\n{context}", system=SYSTEM_PROMPT, purpose="repository_orientation"
    )
    summary, content = parse_guide(data)
    return summary, content, result.provider, result.model


def upsert_guide(
    db: Session,
    repository_id: int,
    *,
    summary: str,
    content: dict,
    provider: str | None,
    model: str | None,
) -> RepositoryGuide:
    guide = db.execute(
        select(RepositoryGuide).where(RepositoryGuide.repository_id == repository_id)
    ).scalar_one_or_none()
    if guide is None:
        guide = RepositoryGuide(repository_id=repository_id)
        db.add(guide)
    guide.summary = summary
    guide.content = content
    guide.provider = provider
    guide.model = model
    db.commit()
    db.refresh(guide)
    return guide
