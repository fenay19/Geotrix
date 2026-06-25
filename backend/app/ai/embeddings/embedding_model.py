"""
Embedding model: converts text into vector representations using OpenAI's
text-embedding-3-small model.

Used by VectorStore for semantic search over events and news.
Falls back to a simple TF-IDF-style term frequency vector if no API key.
"""

import logging
import math
from typing import Any, Optional

from ...utils.api_clients import api_client
from ...core.constants import OPENAI_EMBEDDINGS_URL, DEFAULT_EMBEDDING_MODEL

logger = logging.getLogger("geotrade.embeddings.model")


import time

def _clean_hf_vector(val: Any) -> Optional[list]:
    if not val:
        return None
    # Recursively drill down to find the list of numbers
    while isinstance(val, list) and len(val) > 0 and isinstance(val[0], list):
        val = val[0]
    if isinstance(val, list) and len(val) > 0 and isinstance(val[0], (int, float)):
        return [float(x) for x in val]
    return None


class EmbeddingModel:
    """
    Converts text into fixed-length float vectors.
    Primary: Local sentence-transformers (all-MiniLM-L6-v2, 384-dim).
    Secondary: Hugging Face Inference API (all-MiniLM-L6-v2, 384-dim).
    Third: OpenAI text-embedding-3-small (1536-dim).
    Fallback: Bag-of-words frequency vector (256-dim).
    """

    FALLBACK_DIM = 256

    def __init__(
        self,
        api_key: Optional[str] = None,
        hf_api_key: Optional[str] = None,
        model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        self.api_key = api_key
        self.hf_api_key = hf_api_key
        self.model = model
        # Set False after first DNS/network failure so we stop retrying HF
        # for the entire session instead of hammering a blocked host.
        self._hf_available: Optional[bool] = None  # None = untested
        self._st_model = None

    def _local_embed(self, text: str) -> Optional[list]:
        if self._st_model is False:
            return None
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._st_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("EmbeddingModel: Local SentenceTransformer ('all-MiniLM-L6-v2') loaded successfully.")
            except Exception as e:
                logger.warning("EmbeddingModel: Failed to load local SentenceTransformer: %s. Disabling local sentence-transformers fallback.", e)
                self._st_model = False
                return None
        try:
            emb = self._st_model.encode(text)
            return [float(x) for x in emb]
        except Exception as e:
            logger.warning("EmbeddingModel: Local embedding generation failed: %s", e)
            return None

    def _local_batch_embed(self, texts: list) -> Optional[list]:
        if self._st_model is False:
            return None
        if self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._st_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("EmbeddingModel: Local SentenceTransformer ('all-MiniLM-L6-v2') loaded successfully.")
            except Exception as e:
                logger.warning("EmbeddingModel: Failed to load local SentenceTransformer: %s. Disabling local sentence-transformers fallback.", e)
                self._st_model = False
                return None
        try:
            embs = self._st_model.encode(texts)
            return [[float(x) for x in emb] for emb in embs]
        except Exception as e:
            logger.warning("EmbeddingModel: Local batch embedding generation failed: %s", e)
            return None

    def get_embedding(self, text: str) -> list:
        """Returns a float vector for the given text."""
        # 1. Local SentenceTransformer (Primary)
        try:
            import sentence_transformers
            result = self._local_embed(text)
            if result is not None:
                return result
        except ImportError:
            pass

        # 2. Hugging Face API
        if self.hf_api_key and self._hf_available is not False:
            result = self._hf_embed(text)
            if result is not None:
                return result

        # 3. OpenAI Embeddings
        if self.api_key:
            result = self._openai_embed(text)
            if result is not None:
                return result

        # 4. Fallback (Bag of Words)
        return self._bow_embed(text)

    def get_batch_embeddings(self, texts: list) -> list:
        """Returns embeddings for a list of texts (batched for efficiency)."""
        # 1. Local SentenceTransformer (Primary)
        try:
            import sentence_transformers
            result = self._local_batch_embed(texts)
            if result is not None:
                return result
        except ImportError:
            pass

        # 2. Hugging Face API
        if self.hf_api_key:
            result = self._hf_batch_embed(texts)
            if result is not None:
                return result

        # 3. OpenAI Embeddings
        if self.api_key:
            result = self._openai_batch_embed(texts)
            if result is not None:
                return result

        # 4. Fallback (Bag of Words)
        return [self._bow_embed(t) for t in texts]

    # ── Hugging Face backend ─────────────────────────────────────────────────

    def _hf_embed(self, text: str) -> Optional[list]:
        # Fast-fail if HF was already confirmed unreachable this session
        if self._hf_available is False:
            return None

        for attempt in range(3):
            try:
                resp = api_client.post_data(
                    "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2",
                    json={"inputs": text},
                    headers={
                        "Authorization": f"Bearer {self.hf_api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=15,
                )
                if isinstance(resp, dict) and "error" in resp and "loading" in resp.get("error", "").lower():
                    wait_time = min(resp.get("estimated_time", 5.0), 10.0)
                    logger.info("Hugging Face model is loading. Waiting %.1f seconds (attempt %d/3)...", wait_time, attempt + 1)
                    time.sleep(wait_time)
                    continue

                vec = _clean_hf_vector(resp)
                if vec:
                    if self._hf_available is None:
                        logger.info("EmbeddingModel: HuggingFace API reachable — using semantic embeddings.")
                    self._hf_available = True
                    return vec
                break
            except Exception as exc:
                exc_str = str(exc)
                # DNS / network failure: disable HF for the rest of the session
                if "NameResolutionError" in exc_str or "getaddrinfo failed" in exc_str or "Failed to resolve" in exc_str:
                    if self._hf_available is not False:  # log only once
                        logger.warning(
                            "EmbeddingModel: HuggingFace host unreachable (DNS failure). "
                            "Disabling HF for this session — falling back to BOW vectors. "
                            "Check your network/firewall or use a VPN."
                        )
                    self._hf_available = False
                    return None
                logger.warning("EmbeddingModel._hf_embed failed: %s", exc)
                break
        return None

    def _hf_batch_embed(self, texts: list) -> Optional[list]:
        if self._hf_available is False:
            return None

        for attempt in range(3):
            try:
                resp = api_client.post_data(
                    "https://api-inference.huggingface.co/models/sentence-transformers/all-MiniLM-L6-v2",
                    json={"inputs": texts},
                    headers={
                        "Authorization": f"Bearer {self.hf_api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=20,
                )
                if isinstance(resp, dict) and "error" in resp and "loading" in resp.get("error", "").lower():
                    wait_time = min(resp.get("estimated_time", 5.0), 10.0)
                    logger.info("Hugging Face model is loading. Waiting %.1f seconds (attempt %d/3)...", wait_time, attempt + 1)
                    time.sleep(wait_time)
                    continue

                if isinstance(resp, list):
                    cleaned = []
                    for item in resp:
                        vec = _clean_hf_vector(item)
                        if vec:
                            cleaned.append(vec)
                        else:
                            return None
                    if len(cleaned) == len(texts):
                        self._hf_available = True
                        return cleaned
                break
            except Exception as exc:
                exc_str = str(exc)
                if "NameResolutionError" in exc_str or "getaddrinfo failed" in exc_str or "Failed to resolve" in exc_str:
                    self._hf_available = False
                    return None
                logger.warning("EmbeddingModel._hf_batch_embed failed: %s", exc)
                break
        return None

    # ── OpenAI backend ───────────────────────────────────────────────────────

    def _openai_embed(self, text: str) -> Optional[list]:
        if "groq.com" in OPENAI_EMBEDDINGS_URL:
            # Groq does not host an embeddings endpoint. Skip to avoid 404 latency.
            return None
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
        if "groq.com" in OPENAI_EMBEDDINGS_URL:
            # Groq does not host an embeddings endpoint. Skip to avoid 404 latency.
            return None
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

embedding_model = EmbeddingModel(
    api_key=_settings.OPENAI_API_KEY,
    hf_api_key=_settings.HUGGINGFACE_API_KEY
)
