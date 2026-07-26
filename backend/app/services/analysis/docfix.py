from __future__ import annotations

from app.ai.providers._common import strip_json_fence
from app.ai.service import AIService

MAX_DOC_CHARS = 12000

SYSTEM_PROMPT = (
    "You are a meticulous technical writer maintaining a software project's "
    "documentation. You are given a documentation file that is now inaccurate "
    "because the code changed, along with a description of the problem and a "
    "suggested fix. Rewrite the file so it is accurate.\n\n"
    "Rules:\n"
    "- Preserve the file's existing structure, tone, and formatting.\n"
    "- Change only what is necessary to fix the described inaccuracy.\n"
    "- Do not invent APIs or behavior that is not supported by the provided context.\n"
    "- Output ONLY the complete updated file content. No commentary, no code fences."
)


async def generate_updated_document(
    ai: AIService,
    *,
    doc_path: str,
    current_content: str,
    drift_summary: str,
    suggested_update: str | None,
    evidence: list[str],
) -> str:
    evidence_block = "\n".join(f"- {item}" for item in evidence) or "- (none provided)"
    prompt = (
        f"Documentation file: {doc_path}\n\n"
        f"Problem detected:\n{drift_summary}\n\n"
        f"Suggested change:\n{suggested_update or '(none provided)'}\n\n"
        f"Supporting evidence:\n{evidence_block}\n\n"
        f"=== Current file content ===\n{current_content[:MAX_DOC_CHARS]}\n\n"
        "Return the complete, corrected file content."
    )
    result = await ai.complete(
        prompt, system=SYSTEM_PROMPT, temperature=0.1, purpose="doc_fix"
    )
    return strip_json_fence(result.text)
