from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.ai.embeddings import EmbeddingService
from app.ai.providers._common import clean_prose
from app.ai.rag import top_k_by_cosine
from app.ai.service import AIService
from app.core.config import get_settings
from app.core.logging import get_logger
from app.models import CodeSymbol, DecisionEntry, Document, KnowledgeEntry
from app.services.symbols import RETRIEVABLE_KINDS

logger = get_logger("variorum.qa")

MAX_ENTRIES = 8
MAX_DECISIONS = 3  # synthesized decisions blended in alongside raw history
MAX_CODE = 5  # code symbols blended in so answers can cite the actual code
MAX_DOCS = 3  # documentation passages blended in
MAX_BODY_CHARS = 600
MIN_SIMILARITY = 0.4  # cosine floor to exclude clearly-unrelated vector hits

# Detected once per process: is the pgvector acceleration path available? True
# only when the `vector` extension is installed AND the `embedding_vec` column
# exists (both created by the guarded pgvector migration). Everywhere else —
# including this dev DB and the test suite — retrieval uses the in-process
# cosine path over the JSONB `embedding` column, which is always present.
_pgvector_active: bool | None = None


def reset_pgvector_detection() -> None:
    """Clear the cached detection (used by tests)."""
    global _pgvector_active
    _pgvector_active = None


def pgvector_active(db: Session) -> bool:
    global _pgvector_active
    if not get_settings().pgvector_enabled:
        return False
    if _pgvector_active is None:
        try:
            _pgvector_active = bool(
                db.execute(
                    text(
                        "SELECT (EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') "
                        "AND EXISTS (SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'knowledge_entries' "
                        "AND column_name = 'embedding_vec'))"
                    )
                ).scalar()
            )
        except Exception:  # noqa: BLE001 — detection must never break retrieval
            _pgvector_active = False
    return _pgvector_active

SYSTEM_PROMPT = (
    "You are Variorum's engineering-memory assistant. Answer the question using "
    "ONLY the numbered context entries below (source code, commits, pull requests, "
    "issues, and synthesized engineering decisions). "
    "Rules:\n"
    "- Base every statement on the provided context; never invent facts, APIs, or "
    "history.\n"
    "- Cite the entries you used only in the `cited` array — never write inline "
    "markers like [1] in the answer text.\n"
    "- Write the answer as clear plain prose (1-4 short paragraphs). No headings, "
    "no bullet lists, no bold/asterisks, no code fences.\n"
    "- If the context does not contain the answer, say you don't have enough "
    "information and cite nothing.\n"
    'Respond in strict JSON: {"answer": string, "cited": [int, ...]}'
)


@dataclass
class Cited:
    """A source the answer drew on — knowledge entry or synthesized decision."""

    kind: str
    source_ref: str
    title: str | None = None
    url: str | None = None


@dataclass
class _ContextDoc:
    """Uniform view of a retrievable source, so knowledge and decisions share one
    numbered-context format and one citation-mapping path."""

    kind: str
    source_ref: str
    title: str | None
    url: str | None
    body: str | None


@dataclass
class QAResult:
    answer: str
    cited_entries: list[Cited]
    provider: str | None
    model: str | None


def _haystack():
    return func.coalesce(KnowledgeEntry.title, "") + " " + func.coalesce(KnowledgeEntry.body, "")


def _merge(
    primary: list[KnowledgeEntry], secondary: list[KnowledgeEntry], k: int
) -> list[KnowledgeEntry]:
    seen: set[int] = set()
    out: list[KnowledgeEntry] = []
    for entry in [*primary, *secondary]:
        if entry.id in seen:
            continue
        seen.add(entry.id)
        out.append(entry)
        if len(out) >= k:
            break
    return out


def retrieve(
    db: Session,
    repository_id: int,
    question: str,
    *,
    k: int = MAX_ENTRIES,
    embedder: EmbeddingService | None = None,
    query_vec: list[float] | None = None,
) -> list[KnowledgeEntry]:
    """Hybrid retrieval: semantic (embedding cosine) blended with keyword
    full-text search. Falls back to keyword-only when embeddings are
    unavailable (no embedder, no quota, or nothing embedded)."""
    keyword_hits = _keyword_retrieve(db, repository_id, question, k)
    if embedder is None or not embedder.available:
        return keyword_hits

    if query_vec is None:
        query_vec = embedder.embed(question)
    if not query_vec:
        return keyword_hits

    if pgvector_active(db):
        vector_hits = _vector_retrieve_pg(db, repository_id, query_vec, k)
    else:
        vector_hits = _vector_retrieve_inprocess(db, repository_id, query_vec, k)

    return _merge(vector_hits, keyword_hits, k)


def _vector_retrieve_inprocess(
    db: Session, repository_id: int, query_vec: list[float], k: int
) -> list[KnowledgeEntry]:
    """Rank JSONB-stored embeddings with pure-Python cosine. Fine at MVP scale;
    the pgvector path replaces this loop with an indexed SQL query."""
    embedded = (
        db.execute(
            select(KnowledgeEntry).where(
                KnowledgeEntry.repository_id == repository_id,
                KnowledgeEntry.embedding.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    return top_k_by_cosine(
        query_vec, embedded, lambda e: e.embedding, k=k, min_similarity=MIN_SIMILARITY
    )


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(repr(float(x)) for x in vec) + "]"


def _vector_retrieve_pg(
    db: Session, repository_id: int, query_vec: list[float], k: int
) -> list[KnowledgeEntry]:
    """Indexed nearest-neighbour search via pgvector's cosine-distance operator.
    Scales to large repositories — the database does the ranking, not Python."""
    max_distance = 1.0 - MIN_SIMILARITY
    rows = db.execute(
        text(
            "SELECT id, embedding_vec <=> (:qvec)::vector AS dist "
            "FROM knowledge_entries "
            "WHERE repository_id = :rid AND embedding_vec IS NOT NULL "
            "ORDER BY dist ASC LIMIT :k"
        ),
        {"qvec": _vector_literal(query_vec), "rid": repository_id, "k": k},
    ).all()
    ids = [row.id for row in rows if row.dist <= max_distance]
    if not ids:
        return []
    entries = (
        db.execute(select(KnowledgeEntry).where(KnowledgeEntry.id.in_(ids))).scalars().all()
    )
    by_id = {e.id: e for e in entries}
    return [by_id[i] for i in ids if i in by_id]


def _keyword_retrieve(
    db: Session, repository_id: int, question: str, k: int
) -> list[KnowledgeEntry]:
    """Full-text retrieval ranked by relevance then recency, with a keyword
    ILIKE fallback for rare identifiers that don't stem."""
    tsv = func.to_tsvector("english", _haystack())
    tsq = func.websearch_to_tsquery("english", question)
    rows = (
        db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.repository_id == repository_id, tsv.op("@@")(tsq))
            .order_by(func.ts_rank(tsv, tsq).desc(), KnowledgeEntry.occurred_at.desc())
            .limit(k)
        )
        .scalars()
        .all()
    )
    if rows:
        return list(rows)

    words = re.findall(r"[A-Za-z0-9_]{3,}", question)[:6]
    if not words:
        return []
    haystack = _haystack()
    clauses = [haystack.ilike(f"%{w}%") for w in words]
    return list(
        db.execute(
            select(KnowledgeEntry)
            .where(KnowledgeEntry.repository_id == repository_id, or_(*clauses))
            .order_by(KnowledgeEntry.occurred_at.desc())
            .limit(k)
        )
        .scalars()
        .all()
    )


def _decision_haystack():
    return func.coalesce(DecisionEntry.title, "") + " " + func.coalesce(DecisionEntry.summary, "")


def _decision_keyword_retrieve(
    db: Session, repository_id: int, question: str, k: int
) -> list[DecisionEntry]:
    """Full-text over decision title+summary, ranked by relevance then recency,
    with an ILIKE fallback (mirrors ``_keyword_retrieve``) so partially-stemming
    phrasings like 'jwt authentication' still surface a 'JWT auth' decision."""
    haystack = _decision_haystack()
    tsv = func.to_tsvector("english", haystack)
    tsq = func.websearch_to_tsquery("english", question)
    rows = (
        db.execute(
            select(DecisionEntry)
            .where(DecisionEntry.repository_id == repository_id, tsv.op("@@")(tsq))
            .order_by(func.ts_rank(tsv, tsq).desc(), DecisionEntry.decided_at.desc().nullslast())
            .limit(k)
        )
        .scalars()
        .all()
    )
    if rows:
        return list(rows)

    words = re.findall(r"[A-Za-z0-9_]{3,}", question)[:6]
    if not words:
        return []
    clauses = [haystack.ilike(f"%{w}%") for w in words]
    return list(
        db.execute(
            select(DecisionEntry)
            .where(DecisionEntry.repository_id == repository_id, or_(*clauses))
            .order_by(DecisionEntry.decided_at.desc().nullslast())
            .limit(k)
        )
        .scalars()
        .all()
    )


def retrieve_decisions(
    db: Session,
    repository_id: int,
    question: str,
    *,
    k: int = MAX_DECISIONS,
    embedder: EmbeddingService | None = None,
    query_vec: list[float] | None = None,
) -> list[DecisionEntry]:
    """Retrieve synthesized decisions relevant to a question — semantic (embedding
    cosine) blended with keyword search, keyword-only when embeddings are
    unavailable. Decisions are few per repo, so this always uses the in-process
    cosine path (no pgvector mirror)."""
    keyword_hits = _decision_keyword_retrieve(db, repository_id, question, k)
    if embedder is None or not embedder.available:
        return keyword_hits
    if query_vec is None:
        query_vec = embedder.embed(question)
    if not query_vec:
        return keyword_hits

    embedded = (
        db.execute(
            select(DecisionEntry).where(
                DecisionEntry.repository_id == repository_id,
                DecisionEntry.embedding.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    vector_hits = top_k_by_cosine(
        query_vec, embedded, lambda d: d.embedding, k=k, min_similarity=MIN_SIMILARITY
    )
    seen: set[int] = set()
    out: list[DecisionEntry] = []
    for d in [*vector_hits, *keyword_hits]:
        if d.id in seen:
            continue
        seen.add(d.id)
        out.append(d)
        if len(out) >= k:
            break
    return out


def retrieve_code(
    db: Session,
    repository_id: int,
    question: str,
    *,
    k: int = MAX_CODE,
    embedder: EmbeddingService | None = None,
    query_vec: list[float] | None = None,
) -> list[CodeSymbol]:
    """Retrieve code symbols relevant to a question — semantic (embedding cosine)
    blended with an identifier keyword match, keyword-only when embeddings are
    unavailable. Lets the Q&A cite the actual functions/classes, not just the
    history written about them."""
    words = re.findall(r"[A-Za-z0-9_]{3,}", question)[:6]
    keyword_hits: list[CodeSymbol] = []
    if words:
        clauses = [CodeSymbol.name.ilike(f"%{w}%") for w in words] + [
            CodeSymbol.path.ilike(f"%{w}%") for w in words
        ]
        keyword_hits = list(
            db.execute(
                select(CodeSymbol)
                .where(
                    CodeSymbol.repository_id == repository_id,
                    CodeSymbol.kind.in_(RETRIEVABLE_KINDS),
                    or_(*clauses),
                )
                .limit(k)
            )
            .scalars()
            .all()
        )
    if embedder is None or not embedder.available:
        return keyword_hits[:k]
    if query_vec is None:
        query_vec = embedder.embed(question)
    if not query_vec:
        return keyword_hits[:k]

    embedded = (
        db.execute(
            select(CodeSymbol).where(
                CodeSymbol.repository_id == repository_id,
                CodeSymbol.kind.in_(RETRIEVABLE_KINDS),
                CodeSymbol.embedding.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    vector_hits = top_k_by_cosine(
        query_vec, embedded, lambda s: s.embedding, k=k, min_similarity=MIN_SIMILARITY
    )
    seen: set[int] = set()
    out: list[CodeSymbol] = []
    for s in [*vector_hits, *keyword_hits]:
        if s.id in seen:
            continue
        seen.add(s.id)
        out.append(s)
        if len(out) >= k:
            break
    return out


def retrieve_docs(
    db: Session,
    repository_id: int,
    question: str,
    *,
    k: int = MAX_DOCS,
    embedder: EmbeddingService | None = None,
    query_vec: list[float] | None = None,
) -> list[Document]:
    """Retrieve documentation relevant to a question — semantic (embedding cosine)
    blended with full-text over title+body, keyword-only when embeddings are
    unavailable. Only docs with stored body are considered."""
    haystack = func.coalesce(Document.title, "") + " " + func.coalesce(Document.body, "")
    tsv = func.to_tsvector("english", haystack)
    tsq = func.websearch_to_tsquery("english", question)
    keyword_hits = list(
        db.execute(
            select(Document)
            .where(
                Document.repository_id == repository_id,
                Document.body.is_not(None),
                tsv.op("@@")(tsq),
            )
            .order_by(func.ts_rank(tsv, tsq).desc())
            .limit(k)
        )
        .scalars()
        .all()
    )
    if not keyword_hits:
        # ILIKE fallback (mirrors _keyword_retrieve) for partially-stemming phrasings.
        words = re.findall(r"[A-Za-z0-9_]{3,}", question)[:6]
        if words:
            clauses = [haystack.ilike(f"%{w}%") for w in words]
            keyword_hits = list(
                db.execute(
                    select(Document)
                    .where(
                        Document.repository_id == repository_id,
                        Document.body.is_not(None),
                        or_(*clauses),
                    )
                    .limit(k)
                )
                .scalars()
                .all()
            )
    if embedder is None or not embedder.available:
        return keyword_hits
    if query_vec is None:
        query_vec = embedder.embed(question)
    if not query_vec:
        return keyword_hits

    embedded = (
        db.execute(
            select(Document).where(
                Document.repository_id == repository_id,
                Document.embedding.is_not(None),
            )
        )
        .scalars()
        .all()
    )
    vector_hits = top_k_by_cosine(
        query_vec, embedded, lambda d: d.embedding, k=k, min_similarity=MIN_SIMILARITY
    )
    seen: set[int] = set()
    out: list[Document] = []
    for d in [*vector_hits, *keyword_hits]:
        if d.id in seen:
            continue
        seen.add(d.id)
        out.append(d)
        if len(out) >= k:
            break
    return out


def _entry_to_doc(e: KnowledgeEntry) -> _ContextDoc:
    return _ContextDoc(
        kind=e.kind.value, source_ref=e.source_ref, title=e.title, url=e.url, body=e.body
    )


def _document_to_doc(
    d: Document, repo_full_name: str | None, default_branch: str
) -> _ContextDoc:
    url = (
        f"https://github.com/{repo_full_name}/blob/{default_branch}/{d.path}"
        if repo_full_name and d.path
        else None
    )
    return _ContextDoc(
        kind="document", source_ref=d.path, title=d.title, url=url, body=d.body
    )


def _code_url(repo_full_name: str | None, default_branch: str, s: CodeSymbol) -> str | None:
    if not repo_full_name or not s.path:
        return None
    anchor = ""
    if s.start_line:
        anchor = f"#L{s.start_line}"
        if s.end_line and s.end_line != s.start_line:
            anchor += f"-L{s.end_line}"
    return f"https://github.com/{repo_full_name}/blob/{default_branch}/{s.path}{anchor}"


def _code_to_doc(
    s: CodeSymbol, repo_full_name: str | None, default_branch: str
) -> _ContextDoc:
    lines = f":{s.start_line}" if s.start_line else ""
    return _ContextDoc(
        kind="code",
        source_ref=f"{s.path}{lines}",
        title=f"{s.name} ({s.kind})",
        url=_code_url(repo_full_name, default_branch, s),
        body=s.signature,
    )


def _decision_to_doc(d: DecisionEntry) -> _ContextDoc:
    return _ContextDoc(
        kind="decision", source_ref=f"DEC-{d.id}", title=d.title, url=None, body=d.summary
    )


def _format_context(docs: list[_ContextDoc]) -> str:
    blocks = []
    for i, d in enumerate(docs, start=1):
        body = (d.body or "").strip()
        if len(body) > MAX_BODY_CHARS:
            body = body[:MAX_BODY_CHARS] + " …"
        blocks.append(
            f"[{i}] {d.kind} {d.source_ref} — {d.title or ''}\n{body}\n(source: {d.url or 'n/a'})"
        )
    return "\n\n".join(blocks)


async def answer_question(
    ai: AIService,
    question: str,
    entries: list[KnowledgeEntry],
    decisions: list[DecisionEntry] | None = None,
    code: list[CodeSymbol] | None = None,
    documents: list[Document] | None = None,
    *,
    repo_full_name: str | None = None,
    default_branch: str = "main",
) -> QAResult:
    """Answer grounded in retrieved context. Blends code symbols, documentation,
    synthesized decisions, and raw history entries when provided (all optional, so
    existing history-only callers are unchanged). Code and doc citations link to
    the source on GitHub."""
    docs = (
        [_entry_to_doc(e) for e in entries]
        + [_decision_to_doc(d) for d in (decisions or [])]
        + [_code_to_doc(s, repo_full_name, default_branch) for s in (code or [])]
        + [_document_to_doc(d, repo_full_name, default_branch) for d in (documents or [])]
    )
    if not docs:
        return QAResult(
            answer=(
                "I don't have enough indexed history to answer that yet. "
                "Try ingesting this repository's history first."
            ),
            cited_entries=[],
            provider=None,
            model=None,
        )

    prompt = f"Question: {question}\n\nContext:\n{_format_context(docs)}"
    data, result = await ai.complete_structured(
        prompt, system=SYSTEM_PROMPT, purpose="engineering_qa"
    )
    answer = clean_prose(str(data.get("answer", "")))
    cited_idx = {
        n for n in (data.get("cited") or []) if isinstance(n, int) and 1 <= n <= len(docs)
    }
    cited = [
        Cited(
            kind=docs[n - 1].kind,
            source_ref=docs[n - 1].source_ref,
            title=docs[n - 1].title,
            url=docs[n - 1].url,
        )
        for n in sorted(cited_idx)
    ]
    return QAResult(
        answer=answer or "I don't have enough information to answer that.",
        cited_entries=cited,
        provider=result.provider,
        model=result.model,
    )
