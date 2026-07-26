from __future__ import annotations

from app.ai.service import AIService
from app.models import KnowledgeEntry

_MAX_CANDIDATES = 8
_MAX_CHANGE_CHARS = 5000

SYSTEM_PROMPT = (
    "You are Variorum's consistency checker. You are given a CODE CHANGE and a "
    "set of numbered RECORDED items from the repository's history (past decisions, "
    "pull requests, issues). Identify only the recorded items that the change "
    "genuinely CONTRADICTS or reverses.\n"
    "Rules:\n"
    "- Report a contradiction only when the change clearly conflicts with a "
    "recorded decision/behavior; do not report mere relatedness.\n"
    "- Cite the item number and explain the contradiction in one sentence.\n"
    "- If nothing is contradicted, return an empty list.\n"
    'Respond in strict JSON: {"contradictions": [{"cited": int, "explanation": string}]}'
)


def build_prompt(change_text: str, entries: list[KnowledgeEntry]) -> str:
    items = []
    for i, e in enumerate(entries, start=1):
        body = (e.body or "").strip().replace("\n", " ")[:400]
        items.append(f"[{i}] {e.kind.value} {e.source_ref} — {e.title or ''}\n{body}")
    return (
        f"CODE CHANGE:\n{change_text[:_MAX_CHANGE_CHARS]}\n\n"
        "RECORDED ITEMS:\n" + "\n\n".join(items)
    )


def parse(data: dict, entries: list[KnowledgeEntry]) -> list[dict]:
    raw = data.get("contradictions")
    if not isinstance(raw, list):
        return []
    out: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cited = item.get("cited")
        explanation = str(item.get("explanation", "")).strip()
        if not isinstance(cited, int) or not (1 <= cited <= len(entries)) or not explanation:
            continue
        e = entries[cited - 1]
        out.append(
            {
                "source": {
                    "kind": e.kind.value,
                    "source_ref": e.source_ref,
                    "title": e.title,
                    "url": e.url,
                },
                "explanation": explanation[:600],
            }
        )
    return out


async def check_contradictions(
    ai: AIService, change_text: str, entries: list[KnowledgeEntry]
) -> list[dict]:
    if not entries or not change_text.strip():
        return []
    candidates = entries[:_MAX_CANDIDATES]
    data, _ = await ai.complete_structured(
        build_prompt(change_text, candidates),
        system=SYSTEM_PROMPT,
        purpose="contradiction_check",
    )
    return parse(data, candidates)
