from __future__ import annotations

from app.ai.rag import cosine, top_k_by_cosine


def test_cosine_basics():
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine([1.0, 0.0], [0.0, 1.0]) == 0.0
    # empty / mismatched-length / zero vectors are safe → 0.0
    assert cosine([], [1.0]) == 0.0
    assert cosine([1.0, 0.0], [1.0]) == 0.0
    assert cosine([0.0, 0.0], [1.0, 1.0]) == 0.0
    # opposite direction is negative
    assert cosine([1.0, 0.0], [-1.0, 0.0]) == -1.0


def test_top_k_ranks_and_filters():
    items = [
        {"id": "a", "vec": [1.0, 0.0, 0.0]},
        {"id": "b", "vec": [0.0, 1.0, 0.0]},
        {"id": "c", "vec": [0.9, 0.1, 0.0]},
        {"id": "d", "vec": None},  # unembedded → treated as similarity 0
    ]
    ranked = top_k_by_cosine(
        [1.0, 0.0, 0.0], items, lambda it: it["vec"], k=2, min_similarity=0.4
    )
    ids = [it["id"] for it in ranked]
    # 'a' (exact) then 'c' (close); 'b' (orthogonal) and 'd' (none) fall below floor
    assert ids == ["a", "c"]


def test_top_k_respects_min_similarity_and_k():
    items = [{"v": [1.0, 0.0]}, {"v": [0.7, 0.7]}, {"v": [0.0, 1.0]}]
    # high floor keeps only the exact match
    assert top_k_by_cosine([1.0, 0.0], items, lambda it: it["v"], k=5, min_similarity=0.95) == [
        {"v": [1.0, 0.0]}
    ]
    # k caps the result size
    assert (
        len(top_k_by_cosine([1.0, 0.0], items, lambda it: it["v"], k=1, min_similarity=0.0)) == 1
    )
