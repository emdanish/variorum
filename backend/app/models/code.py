from __future__ import annotations

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import DocumentKind, LinkSource


class CodeSymbol(Base, TimestampMixin):
    __tablename__ = "code_symbols"
    __table_args__ = (Index("ix_code_symbols_repo_path", "repository_id", "path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str | None] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    signature: Mapped[str | None] = mapped_column(Text)
    # Semantic-search embedding of the symbol (name + path + signature), so the
    # engineering-memory Q&A can retrieve and cite the actual code, not just the
    # history written about it. JSONB + in-process cosine, same as elsewhere.
    embedding: Mapped[list[float] | None] = mapped_column(JSONB)


class Document(Base, TimestampMixin):
    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_repo_path", "repository_id", "path"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    kind: Mapped[DocumentKind] = mapped_column(default=DocumentKind.markdown, nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    # Stored documentation text (truncated), so the Q&A can retrieve and cite the
    # actual passages — not just link to the file.
    body: Mapped[str | None] = mapped_column(Text)
    # Semantic-search embedding of title + body (JSONB + in-process cosine).
    embedding: Mapped[list[float] | None] = mapped_column(JSONB)


class DocCodeLink(Base, TimestampMixin):
    __tablename__ = "doc_code_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    symbol_id: Mapped[int | None] = mapped_column(
        ForeignKey("code_symbols.id", ondelete="SET NULL")
    )
    path: Mapped[str | None] = mapped_column(String(1024))
    confidence: Mapped[float] = mapped_column(default=0.0, nullable=False)
    source: Mapped[LinkSource] = mapped_column(default=LinkSource.heuristic, nullable=False)
