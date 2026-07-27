from __future__ import annotations

import math
from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two equal-length vectors; 0.0 for empty/mismatched."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def top_k_by_cosine(
    query_vec: list[float],
    items: Iterable[T],
    get_vec: Callable[[T], list[float] | None],
    *,
    k: int,
    min_similarity: float,
) -> list[T]:
    """Rank items by cosine similarity to ``query_vec`` (in-process), keeping only
    those at or above ``min_similarity`` and returning the top ``k``.

    This is the shared semantic-ranking primitive for JSONB-stored embeddings:
    fine at repository scale, and the same abstraction any future embedded
    content type (knowledge, decisions, …) can reuse. The pgvector path replaces
    this loop with an indexed SQL query for large corpora.
    """
    scored: list[tuple[float, T]] = []
    for item in items:
        score = cosine(query_vec, get_vec(item) or [])
        if score >= min_similarity:
            scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _score, item in scored[:k]]
