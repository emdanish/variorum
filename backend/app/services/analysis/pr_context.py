from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CodeSymbol, DocCodeLink, Document


@dataclass
class DriftCandidate:
    document_id: int
    document_path: str
    document_title: str | None
    trigger_paths: list[str] = field(default_factory=list)
    symbol_names: list[str] = field(default_factory=list)


def build_candidates(
    db: Session, repository_id: int, changed_paths: set[str]
) -> list[DriftCandidate]:
    """Find documents whose linked code changed in this PR. A document is a
    candidate when it links (by path or via a symbol) to a changed file."""
    if not changed_paths:
        return []

    rows = db.execute(
        select(
            Document.id,
            Document.path,
            Document.title,
            DocCodeLink.path,
            CodeSymbol.path,
            CodeSymbol.name,
        )
        .join(DocCodeLink, DocCodeLink.document_id == Document.id)
        .join(CodeSymbol, DocCodeLink.symbol_id == CodeSymbol.id, isouter=True)
        .where(Document.repository_id == repository_id)
    ).all()

    candidates: dict[int, DriftCandidate] = {}
    for doc_id, doc_path, doc_title, link_path, sym_path, sym_name in rows:
        triggered: str | None = None
        if link_path and link_path in changed_paths:
            triggered = link_path
        elif sym_path and sym_path in changed_paths:
            triggered = sym_path
        if triggered is None:
            continue

        candidate = candidates.setdefault(
            doc_id, DriftCandidate(doc_id, doc_path, doc_title)
        )
        if triggered not in candidate.trigger_paths:
            candidate.trigger_paths.append(triggered)
        if sym_name and sym_path in changed_paths and sym_name not in candidate.symbol_names:
            candidate.symbol_names.append(sym_name)

    return list(candidates.values())
