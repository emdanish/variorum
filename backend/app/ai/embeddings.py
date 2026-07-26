from __future__ import annotations

from functools import lru_cache

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("variorum.embeddings")

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_BATCH_SIZE = 100
_MAX_TEXT_CHARS = 8000


class EmbeddingService:
    """Text embeddings via Google's embedding model. Embeddings are Gemini-only
    among our providers (DeepSeek/Perplexity don't offer a compatible endpoint),
    so this falls back across the two Gemini keys and returns None if none work —
    callers then degrade to keyword search."""

    def __init__(
        self,
        api_keys: list[str],
        *,
        model: str = "gemini-embedding-001",
        dim: int = 768,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._keys = [k for k in api_keys if k]
        self._model = model
        self._dim = dim
        self._transport = transport

    @property
    def available(self) -> bool:
        return bool(self._keys)

    def embed(self, text: str) -> list[float] | None:
        result = self.embed_batch([text])
        return result[0] if result else None

    def embed_batch(self, texts: list[str]) -> list[list[float]] | None:
        if not self._keys or not texts:
            return None
        for key in self._keys:
            try:
                return self._embed_with_key(key, texts)
            except Exception as exc:  # noqa: BLE001 — try the next key, then give up
                logger.warning("embedding failed (trying next key): %s", str(exc)[:160])
        return None

    def _embed_with_key(self, key: str, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        url = f"{_BASE_URL}/models/{self._model}:batchEmbedContents"
        headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
        with httpx.Client(timeout=60.0, transport=self._transport) as client:
            for start in range(0, len(texts), _BATCH_SIZE):
                chunk = texts[start : start + _BATCH_SIZE]
                body = {
                    "requests": [
                        {
                            "model": f"models/{self._model}",
                            "content": {"parts": [{"text": (t or "")[:_MAX_TEXT_CHARS]}]},
                            "outputDimensionality": self._dim,
                        }
                        for t in chunk
                    ]
                }
                resp = client.post(url, headers=headers, json=body)
                resp.raise_for_status()
                embeddings = resp.json().get("embeddings", [])
                out.extend(e.get("values", []) for e in embeddings)
        return out


@lru_cache
def get_embedding_service() -> EmbeddingService:
    s = get_settings()
    return EmbeddingService([s.gemini_api_key_1, s.gemini_api_key_2])
