from __future__ import annotations

from dataclasses import dataclass

from app.ai.service import AIService
from app.models import DriftSeverity

MAX_DOC_CHARS = 6000
MAX_DIFF_CHARS = 6000

SYSTEM_PROMPT = (
    "You are a documentation drift detector for a software repository. You are "
    "given a documentation file and the code changes from a pull request that "
    "affect code the documentation references. Decide whether the documentation "
    "is now inaccurate or outdated because of those changes.\n\n"
    "Rules:\n"
    "- Only report drift you can justify with specific evidence from the diff.\n"
    "- If the documentation is still accurate, set drifted to false.\n"
    "- Never invent APIs, files, or behavior.\n"
    "Respond with strict JSON matching:\n"
    '{"drifted": boolean, "severity": "info|low|medium|high", '
    '"summary": string, "evidence": [string, ...], '
    '"suggested_update": string|null}'
)


@dataclass
class ChangedFileDiff:
    path: str
    patch: str | None


@dataclass
class DriftVerdict:
    drifted: bool
    severity: DriftSeverity
    summary: str
    evidence: list[str]
    suggested_update: str | None
    provider: str | None
    model: str | None


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n… [truncated]"


def build_drift_prompt(
    doc_path: str,
    doc_content: str,
    affected_symbols: list[str],
    diffs: list[ChangedFileDiff],
) -> str:
    symbols = ", ".join(sorted(set(affected_symbols))) or "(none identified)"
    diff_blocks = []
    remaining = MAX_DIFF_CHARS
    for diff in diffs:
        if not diff.patch or remaining <= 0:
            continue
        chunk = _truncate(diff.patch, remaining)
        remaining -= len(chunk)
        diff_blocks.append(f"--- {diff.path} ---\n{chunk}")
    diffs_text = "\n\n".join(diff_blocks) or "(no textual diff available)"

    return (
        f"Documentation file: {doc_path}\n"
        f"Symbols this documentation references that changed: {symbols}\n\n"
        f"=== Current documentation content ===\n"
        f"{_truncate(doc_content, MAX_DOC_CHARS)}\n\n"
        f"=== Code changes in the pull request ===\n"
        f"{diffs_text}\n\n"
        "Assess whether the documentation has drifted and respond with the "
        "required JSON."
    )


def _coerce_severity(value: object) -> DriftSeverity:
    try:
        return DriftSeverity(str(value).lower())
    except ValueError:
        return DriftSeverity.low


async def assess_document_drift(
    ai: AIService,
    *,
    doc_path: str,
    doc_content: str,
    affected_symbols: list[str],
    diffs: list[ChangedFileDiff],
) -> DriftVerdict:
    prompt = build_drift_prompt(doc_path, doc_content, affected_symbols, diffs)
    data, result = await ai.complete_structured(
        prompt, system=SYSTEM_PROMPT, purpose="doc_drift"
    )

    drifted = bool(data.get("drifted"))
    evidence = [str(item)[:500] for item in (data.get("evidence") or [])][:10]
    suggested = data.get("suggested_update")
    return DriftVerdict(
        drifted=drifted,
        severity=_coerce_severity(data.get("severity", "low")) if drifted else DriftSeverity.info,
        summary=str(data.get("summary", ""))[:2000],
        evidence=evidence,
        suggested_update=str(suggested) if suggested else None,
        provider=result.provider,
        model=result.model,
    )
