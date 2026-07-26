from __future__ import annotations

import json

import httpx

from app.ai.embeddings import EmbeddingService


def test_embed_batch_returns_vectors():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("batchEmbedContents")
        n = len(json.loads(request.content)["requests"])
        return httpx.Response(200, json={"embeddings": [{"values": [0.1, 0.2, 0.3]}] * n})

    svc = EmbeddingService(["k1"], transport=httpx.MockTransport(handler))
    out = svc.embed_batch(["a", "b"])
    assert out == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert svc.embed("x") == [0.1, 0.2, 0.3]


def test_embed_falls_back_across_keys():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers.get("x-goog-api-key") == "bad":
            return httpx.Response(403, json={"error": "no access"})
        return httpx.Response(200, json={"embeddings": [{"values": [1.0]}]})

    svc = EmbeddingService(["bad", "good"], transport=httpx.MockTransport(handler))
    assert svc.embed("x") == [1.0]


def test_embed_returns_none_when_all_keys_fail():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "down"})

    svc = EmbeddingService(["k1", "k2"], transport=httpx.MockTransport(handler))
    assert svc.embed("x") is None


def test_unavailable_without_keys():
    svc = EmbeddingService([])
    assert svc.available is False
    assert svc.embed("x") is None
    assert svc.embed_batch(["a"]) is None
