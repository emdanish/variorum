from __future__ import annotations

from app.services.analysis.docfix import generate_updated_document
from tests._fakes import FakeAI


async def test_generate_updated_document_returns_text():
    ai = FakeAI(text="# Auth\n\nUses JWT tokens.\n")
    result = await generate_updated_document(
        ai,
        doc_path="docs/auth.md",
        current_content="# Auth\n\nUses session cookies.\n",
        drift_summary="Auth switched to JWT",
        suggested_update="Describe JWT",
        evidence=["diff shows jwt"],
    )
    assert "JWT" in result
    # the prompt should carry the current content + problem
    assert any("session cookies" in c for c in ai.calls)


async def test_generate_updated_document_strips_code_fence():
    ai = FakeAI(text="```markdown\n# Title\n\nBody\n```")
    result = await generate_updated_document(
        ai,
        doc_path="d.md",
        current_content="old",
        drift_summary="s",
        suggested_update=None,
        evidence=[],
    )
    assert result.startswith("# Title")
    assert "```" not in result
