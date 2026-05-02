"""
In-memory vector store for semantic search over geopolitical events and news.

Uses cosine similarity to find the most relevant stored vectors for a query.
This is a lightweight alternative to FAISS/Chroma — no extra dependencies.
For production scale, swap the _store with a FAISS index or ChromaDB client.
"""

import math
import logging
from typing import Any, Optional

logger = logging.getLogger("geotrade.embeddings.vector_store")


def _cosine_similarity(a: list, b: list) -> float:
    """Computes cosine similarity between two equal-length float vectors."""
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    denom = mag_a * mag_b
    return dot / denom if denom else 0.0


class VectorStore:
    """
    Simple in-memory semantic vector store.

    Storage format:
        _store = {
            "<id>": {"vector": list[float], "metadata": dict}
        }
    """

    def __init__(self):
        self._store: dict[str, dict] = {}

    def warm_up(self) -> None:
        """
        Warms up the vector store. For the in-memory version, this is a no-op.
        In a production version (FAISS/Chroma), this would load the index from disk.
        """
        logger.info("VectorStore: warm-up complete (in-memory mode).")

    def add_vector(self, id: str, vector: list, metadata: Any = None) -> None:
        """
        Adds or updates a vector in the store.

        Args:
            id:       Unique string identifier (e.g. "event_42")
            vector:   Float embedding vector
            metadata: Any dict to store alongside (e.g. title, event_type)
        """
        self._store[id] = {"vector": vector, "metadata": metadata or {}}
        logger.debug("VectorStore: stored vector id=%s (dim=%d)", id, len(vector))

    def search(
        self,
        query_vector: list,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list:
        """
        Returns the top-k most similar items to query_vector.

        Args:
            query_vector: Float embedding of the query
            top_k:        Number of results to return
            min_score:    Minimum cosine similarity threshold (0-1)

        Returns:
            List of dicts: [{"id": str, "score": float, "metadata": dict}, ...]
        """
        if not self._store or not query_vector:
            return []

        scored = []
        for item_id, item in self._store.items():
            score = _cosine_similarity(query_vector, item["vector"])
            if score >= min_score:
                scored.append({"id": item_id, "score": round(score, 4), "metadata": item["metadata"]})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def delete(self, id: str) -> bool:
        """Removes a vector from the store. Returns True if found."""
        if id in self._store:
            del self._store[id]
            return True
        return False

    def clear(self) -> None:
        """Wipes the entire store."""
        self._store.clear()

    def count(self) -> int:
        """Returns the number of stored vectors."""
        return len(self._store)


# Singleton — shared across services in the same process
vector_store = VectorStore()
