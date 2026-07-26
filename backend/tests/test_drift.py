from __future__ import annotations

from app.models import DriftSeverity
from app.services.analysis.drift import (
    ChangedFileDiff,
    assess_document_drift,
    build_drift_prompt,
)
from tests._fakes import FakeAI


def test_build_drift_prompt_includes_context():
    prompt = build_drift_prompt(
        "docs/auth.md",
        "Authentication uses session cookies.",
        ["login", "logout"],
        [ChangedFileDiff(path="src/auth.py", patch="@@ -1 +1 @@\n-cookie\n+jwt")],
    )
    assert "docs/auth.md" in prompt
    assert "login" in prompt and "logout" in prompt
    assert "src/auth.py" in prompt
    assert "jwt" in prompt


def test_build_drift_prompt_truncates_long_content():
    prompt = build_drift_prompt("d.md", "x" * 20000, [], [])
    assert "[truncated]" in prompt


async def test_assess_reports_drift_with_provenance():
    ai = FakeAI(
        {
            "drifted": True,
            "severity": "high",
            "summary": "Auth switched from cookies to JWT",
            "evidence": ["diff replaces cookie with jwt"],
            "suggested_update": "Describe the JWT flow.",
        }
    )
    verdict = await assess_document_drift(
        ai,
        doc_path="docs/auth.md",
        doc_content="Uses cookies.",
        affected_symbols=["login"],
        diffs=[ChangedFileDiff("src/auth.py", "+jwt")],
    )
    assert verdict.drifted is True
    assert verdict.severity == DriftSeverity.high
    assert verdict.provider == "gemini-1"
    assert verdict.model == "gemini-test"
    assert verdict.suggested_update == "Describe the JWT flow."
    assert verdict.evidence == ["diff replaces cookie with jwt"]


async def test_assess_no_drift_uses_info_severity():
    ai = FakeAI({"drifted": False, "severity": "high", "summary": "still accurate"})
    verdict = await assess_document_drift(
        ai, doc_path="d.md", doc_content="c", affected_symbols=[], diffs=[]
    )
    assert verdict.drifted is False
    assert verdict.severity == DriftSeverity.info


async def test_assess_coerces_unknown_severity():
    ai = FakeAI({"drifted": True, "severity": "catastrophic", "summary": "x"})
    verdict = await assess_document_drift(
        ai, doc_path="d.md", doc_content="c", affected_symbols=[], diffs=[]
    )
    assert verdict.severity == DriftSeverity.low
