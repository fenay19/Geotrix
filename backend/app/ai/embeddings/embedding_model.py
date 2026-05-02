"""
Embedding model: converts text into vector representations using OpenAI's
text-embedding-3-small model.

Used by VectorStore for semantic search over events and news.
Falls back to a simple TF-IDF-style term frequency vector if no API key.
"""

import logging
import math
from typing import Optional

from ...utils.api_clients import api_client
from ...core.constants import OPENAI_EMBEDDINGS_URL, DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger("geotrade.embeddings.model")


class EmbeddingModel:
    """
    Converts text into fixed-length float vectors.
    Primary: OpenAI text-embedding-3-small (1536-dim).
    Fallback: Bag-of-words frequency vector (256-dim).
    """

    FALLBACK_DIM = 256

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_EMBEDDING_MODEL):
        self.api_key = api_key
        self.model = model

    def get_embedding(self, text: str) -> list:
        """Returns a float vector for the given text."""
        if self.api_key:
            result = self._openai_embed(text)
            if result:
                return result
        return self._bow_embed(text)

    def get_batch_embeddings(self, texts: list) -> list:
        """Returns embeddings for a list of texts (batched for efficiency)."""
        if self.api_key:
            result = self._openai_batch_embed(texts)
            if result:
                return result
        return [self._bow_embed(t) for t in texts]

    # ── OpenAI backend ───────────────────────────────────────────────────────

    def _openai_embed(self, text: str) -> Optional[list]:
        try:
            resp = api_client.post_data(
                OPENAI_EMBEDDINGS_URL,
                json={"model": self.model, "input": text[:8000]},
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            return resp["data"][0]["embedding"]
        except Exception as exc:
            logger.warning("EmbeddingModel._openai_embed failed: %s", exc)
            return None

    def _openai_batch_embed(self, texts: list) -> Optional[list]:
        try:
            resp = api_client.post_data(
                OPENAI_EMBEDDINGS_URL,
                json={"model": self.model, "input": [t[:8000] for t in texts]},
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=20,
            )
            items = sorted(resp["data"], key=lambda x: x["index"])
            return [item["embedding"] for item in items]
        except Exception as exc:
            logger.warning("EmbeddingModel._openai_batch_embed failed: %s", exc)
            return None

    # ── Fallback: bag-of-words hash vector ───────────────────────────────────

    def _bow_embed(self, text: str) -> list:
        """
        Produces a deterministic FALLBACK_DIM-dimensional frequency vector
        using character n-gram hashing. Useful for testing without an API key.
        """
        vec = [0.0] * self.FALLBACK_DIM
        words = text.lower().split()
        for word in words:
            idx = hash(word) % self.FALLBACK_DIM
            vec[idx] += 1.0
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [round(v / norm, 6) for v in vec]


from ...config import settings as _settings  # noqa: E402

embedding_model = EmbeddingModel(api_key=_settings.OPENAI_API_KEY)
