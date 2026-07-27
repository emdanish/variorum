from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import CodeSymbol, DocCodeLink, Document, DocumentKind, LinkSource, Repository
from app.services.indexer.code_index import index_directory
from app.services.indexer.docs import discover_documents
from app.services.indexer.linker import link_documents

_MAX_DOC_BODY = 20_000  # cap stored doc text so a row stays reasonable


@dataclass
class IndexResult:
    files: int
    symbols: int
    documents: int
    links: int


def _clear_existing(db: Session, repository_id: int) -> None:
    doc_ids = select(Document.id).where(Document.repository_id == repository_id)
    db.execute(delete(DocCodeLink).where(DocCodeLink.document_id.in_(doc_ids)))
    db.execute(delete(Document).where(Document.repository_id == repository_id))
    db.execute(delete(CodeSymbol).where(CodeSymbol.repository_id == repository_id))
    db.flush()


def reindex_repository(db: Session, repo: Repository, root: Path) -> IndexResult:
    """Replace the stored index for a repository with a fresh structural scan of
    `root` (an extracted working tree). Idempotent: safe to re-run."""
    file_symbols = index_directory(root)
    docs = discover_documents(root)
    links = link_documents(docs, file_symbols)

    _clear_existing(db, repo.id)

    symbol_count = 0
    for file in file_symbols:
        for symbol in file.symbols:
            db.add(
                CodeSymbol(
                    repository_id=repo.id,
                    path=file.path,
                    language=symbol.language,
                    kind=symbol.kind,
                    name=symbol.name,
                    start_line=symbol.start_line,
                    end_line=symbol.end_line,
                    signature=symbol.signature,
                )
            )
            symbol_count += 1
    db.flush()

    symbol_id_by_key: dict[tuple[str, str], int] = {}
    symbol_rows = db.execute(
        select(CodeSymbol.id, CodeSymbol.path, CodeSymbol.name).where(
            CodeSymbol.repository_id == repo.id
        )
    ).all()
    for sid, path, name in symbol_rows:
        symbol_id_by_key.setdefault((path, name), sid)

    for doc in docs:
        db.add(
            Document(
                repository_id=repo.id,
                path=doc.path,
                kind=DocumentKind.markdown,
                title=doc.title,
                content_hash=doc.content_hash,
                body=(doc.content or "")[:_MAX_DOC_BODY] or None,
            )
        )
    db.flush()

    doc_rows = db.execute(
        select(Document.path, Document.id).where(Document.repository_id == repo.id)
    ).tuples().all()
    doc_id_by_path: dict[str, int] = dict(doc_rows)

    link_count = 0
    for link in links:
        document_id = doc_id_by_path.get(link.doc_path)
        if document_id is None:
            continue
        symbol_id = (
            symbol_id_by_key.get((link.path, link.symbol_name))
            if link.symbol_name
            else None
        )
        db.add(
            DocCodeLink(
                document_id=document_id,
                symbol_id=symbol_id,
                path=link.path,
                confidence=link.confidence,
                source=LinkSource.heuristic,
            )
        )
        link_count += 1

    db.flush()
    return IndexResult(
        files=len(file_symbols),
        symbols=symbol_count,
        documents=len(docs),
        links=link_count,
    )
