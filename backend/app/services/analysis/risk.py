from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.service import AIService
from app.models import CodeSymbol, DriftSeverity
from app.services.github.client import ChangedFile
from app.services.indexer.languages import spec_for_path

MAX_DIFF_CHARS = 6000

_TEST_PATH_RE = re.compile(
    r"(^|/)(tests?|__tests__|spec)(/|$)"  # a tests/spec directory
    r"|(^|/)test_[^/]+$"  # test_foo.py
    r"|_test\.[a-z]+$"  # foo_test.go
    r"|\.(test|spec)\.[a-z]+$",  # foo.test.ts / foo.spec.ts
    re.IGNORECASE,
)

SYSTEM_PROMPT = (
    "You are a software test-risk analyst. Given the diff for a changed source "
    "file and whether it currently has tests, assess the risk this change "
    "introduces and identify concrete scenarios that appear untested.\n\n"
    "Rules:\n"
    "- Base your assessment on the diff; do not invent behavior.\n"
    "- 'untested_scenarios' must be specific and testable (e.g. 'duplicate "
    "payment submission', not 'edge cases').\n"
    "- risk_level is one of: low, medium, high.\n"
    'Respond in strict JSON: {"risk_level": string, "summary": string, '
    '"untested_scenarios": [string, ...]}'
)


def is_test_path(path: str) -> bool:
    return bool(_TEST_PATH_RE.search(path))


def is_source_path(path: str) -> bool:
    return spec_for_path(path) is not None and not is_test_path(path)


@dataclass
class FileSignals:
    path: str
    churn: int
    symbol_count: int
    has_tests: bool


@dataclass
class RiskVerdict:
    risk_level: DriftSeverity
    summary: str
    untested_scenarios: list[str] = field(default_factory=list)
    provider: str | None = None
    model: str | None = None


def _stem(path: str) -> str:
    return path.rsplit("/", 1)[-1].rsplit(".", 1)[0]


def compute_signals(db: Session, repository_id: int, changed: ChangedFile) -> FileSignals:
    symbols = (
        db.execute(
            select(CodeSymbol.path, CodeSymbol.name, CodeSymbol.kind).where(
                CodeSymbol.repository_id == repository_id
            )
        )
        .all()
    )
    symbol_count = sum(1 for path, _n, _k in symbols if path == changed.path)

    stem = _stem(changed.path).lower()
    has_tests = False
    for path, name, kind in symbols:
        if not is_test_path(path):
            continue
        # A test file whose name references the changed file, or an import in a
        # test file that mentions the changed module.
        if stem and (stem in _stem(path).lower() or (kind == "import" and stem in name.lower())):
            has_tests = True
            break

    return FileSignals(
        path=changed.path,
        churn=changed.additions + changed.deletions,
        symbol_count=symbol_count,
        has_tests=has_tests,
    )


def _coerce_level(value: object) -> DriftSeverity:
    try:
        level = DriftSeverity(str(value).lower())
    except ValueError:
        return DriftSeverity.medium
    return level if level != DriftSeverity.info else DriftSeverity.low


async def assess_risk(
    ai: AIService, *, path: str, patch: str | None, signals: FileSignals
) -> RiskVerdict:
    diff = (patch or "(no textual diff available)")[:MAX_DIFF_CHARS]
    prompt = (
        f"Changed source file: {path}\n"
        f"Lines changed (churn): {signals.churn}\n"
        f"Symbols defined in this file: {signals.symbol_count}\n"
        f"Has tests referencing this file: {'yes' if signals.has_tests else 'no'}\n\n"
        f"=== Diff ===\n{diff}\n\n"
        "Assess the risk and list untested scenarios as required JSON."
    )
    data, result = await ai.complete_structured(prompt, system=SYSTEM_PROMPT, purpose="test_risk")
    scenarios = [str(s)[:300] for s in (data.get("untested_scenarios") or [])][:12]
    return RiskVerdict(
        risk_level=_coerce_level(data.get("risk_level", "medium")),
        summary=str(data.get("summary", ""))[:2000],
        untested_scenarios=scenarios,
        provider=result.provider,
        model=result.model,
    )
