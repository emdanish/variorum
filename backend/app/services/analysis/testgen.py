from __future__ import annotations

from app.ai.providers._common import unwrap_sole_code_fence
from app.ai.service import AIService

SOURCE_MAX_CHARS = 12000

SYSTEM_PROMPT = (
    "You are a software engineer writing automated tests. Given a source file "
    "and a list of scenarios that appear untested, write a NEW test file that "
    "covers those scenarios.\n\n"
    "Rules:\n"
    "- Match the source language and, where evident from the source, the "
    "project's test framework and import conventions.\n"
    "- Write focused, runnable tests for the listed scenarios; do not test "
    "unrelated code.\n"
    "- Output ONLY the test file content. No markdown, no commentary, no code "
    "fences."
)


def test_path_for(source_path: str, language: str) -> str:
    """A non-colliding path for the generated tests (marked `variorum` so it
    never overwrites the project's own tests)."""
    directory, _, filename = source_path.rpartition("/")
    stem = filename.rsplit(".", 1)[0]
    if language == "python":
        return f"tests/test_{stem}_variorum.py"
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "js"
    name = f"{stem}.variorum.test.{ext}"
    return f"{directory}/{name}" if directory else name


async def generate_test_file(
    ai: AIService,
    *,
    source_path: str,
    source_content: str,
    untested_scenarios: list[str],
    language: str,
) -> str:
    scenarios = "\n".join(f"- {s}" for s in untested_scenarios) or "- general correctness"
    prompt = (
        f"Source file: {source_path}\n"
        f"Language: {language}\n\n"
        f"Scenarios to cover:\n{scenarios}\n\n"
        f"=== Source ===\n{source_content[:SOURCE_MAX_CHARS]}\n\n"
        "Write the complete test file content."
    )
    result = await ai.complete(
        prompt, system=SYSTEM_PROMPT, temperature=0.1, purpose="test_gen"
    )
    return unwrap_sole_code_fence(result.text)
