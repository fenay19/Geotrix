"""
Persistent FAISS vector store for semantic search over geopolitical events and news.

Uses FAISS (Facebook AI Similarity Search) with Inner Product index.
Since OpenAI embeddings are L2 normalized, the Inner Product is mathematically
equivalent to Cosine Similarity.

Falls back gracefully to a dictionary-based in-memory cosine similarity search
if faiss-cpu is not installed or raises an error.
"""

import os
import json
import math
import logging
from typing import Any, Optional
import numpy as np

logger = logging.getLogger("geotrade.embeddings.vector_store")

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    logger.warning("faiss-cpu is not installed. VectorStore falling back to in-memory dictionary mode.")

# Resolve save directory dynamically (backend/app/ml/saved_models)
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
save_dir = os.path.abspath(os.path.join(backend_dir, "app", "ml", "saved_models"))
INDEX_PATH = os.path.join(save_dir, "vector_store.index")
META_PATH = os.path.join(save_dir, "vector_store_meta.json")


def _cosine_similarity(a: list, b: list) -> float:
    """Computes cosine similarity between two equal-length float vectors (fallback)."""
    dot   = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(y * y for y in b))
    denom = mag_a * mag_b
    return dot / denom if denom else 0.0


class VectorStore:
    """
    Semantic vector store using FAISS CPU with disk persistence.
    """

    def __init__(self):
        self._vectors: dict[str, list] = {}
        self.metadata: dict[str, dict] = {}
        self.ids: list[str] = []
        self.index = None
        self.dim = None

    def warm_up(self) -> None:
        """Loads the FAISS index and metadata from disk if they exist."""
        if not HAS_FAISS:
            logger.info("VectorStore: warm-up complete (in-memory dictionary fallback).")
            return

        try:
            if os.path.exists(META_PATH) and os.path.exists(INDEX_PATH):
                with open(META_PATH, "r") as f:
                    meta_data = json.load(f)
                    self._vectors = meta_data.get("vectors", {})
                    self.metadata = meta_data.get("metadata", {})
                    self.ids = meta_data.get("ids", [])
                    self.dim = meta_data.get("dim")
                
                if self.ids and self.dim:
                    self.index = faiss.read_index(INDEX_PATH)
                    logger.info("VectorStore: FAISS index loaded successfully from %s. Total vectors: %d", INDEX_PATH, self.count())
                else:
                    logger.info("VectorStore: Index files are empty. Ready for indexing.")
            else:
                logger.info("VectorStore: No existing FAISS index found. Ready for indexing.")
        except Exception as e:
            logger.error("VectorStore warm_up failed to load index: %s. Starting with empty store.", e)
            self.clear()

    def _save(self) -> None:
        """Persists the FAISS index and metadata to disk."""
        if not HAS_FAISS:
            return
        try:
            os.makedirs(save_dir, exist_ok=True)
            meta_data = {
                "vectors": self._vectors,
                "metadata": self.metadata,
                "ids": self.ids,
                "dim": self.dim
            }
            with open(META_PATH, "w") as f:
                json.dump(meta_data, f)
            
            if self.index:
                faiss.write_index(self.index, INDEX_PATH)
            elif os.path.exists(INDEX_PATH):
                os.remove(INDEX_PATH)
        except Exception as e:
            logger.error("VectorStore failed to save index to disk: %s", e)

    def _rebuild_index(self) -> None:
        """Rebuilds the FAISS index from the current in-memory vectors list."""
        if not HAS_FAISS:
            return
        if not self.ids or not self.dim:
            self.index = None
            return
        self.index = faiss.IndexFlatIP(self.dim)
        vectors_np = np.array([self._vectors[vid] for vid in self.ids], dtype=np.float32)
        # Normalize for Inner Product (makes IP search identical to Cosine Similarity)
        norms = np.linalg.norm(vectors_np, axis=1, keepdims=True)
        # Prevent division by zero
        norms[norms == 0] = 1.0
        normalized_vectors = vectors_np / norms
        self.index.add(normalized_vectors)

    def add_vector(self, id: str, vector: list, metadata: Any = None) -> None:
        """Adds or updates a vector in the store."""
        if not HAS_FAISS:
            # Fallback dictionary mode
            if id not in self._vectors:
                self.ids.append(id)
            self._vectors[id] = vector
            self.metadata[id] = metadata or {}
            logger.debug("VectorStore (Fallback): stored vector id=%s", id)
            return

        try:
            # Determine or verify dimension
            if self.dim is None:
                self.dim = len(vector)
            elif len(vector) != self.dim:
                raise ValueError(f"Vector dimension mismatch: expected {self.dim}, got {len(vector)}")

            # Update vectors list and metadata
            is_new = id not in self._vectors
            self._vectors[id] = vector
            self.metadata[id] = metadata or {}
            
            if is_new:
                self.ids.append(id)
                
            # If the vector exists, we need to rebuild the FAISS index to update it.
            # If it's a new vector and index is initialized, we can just add it.
            if self.index is None:
                self._rebuild_index()
            elif not is_new:
                self._rebuild_index()
            else:
                vec_np = np.array([vector], dtype=np.float32)
                norm = np.linalg.norm(vec_np)
                if norm == 0:
                    norm = 1.0
                normalized_vec = vec_np / norm
                self.index.add(normalized_vec)
                
            self._save()
            logger.debug("VectorStore: stored vector id=%s (dim=%d)", id, len(vector))
        except Exception as e:
            logger.error("VectorStore failed to add vector %s: %s", id, e)

    def search(
        self,
        query_vector: list,
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> list:
        """Returns the top-k most similar items to query_vector."""
        if not query_vector:
            return []

        # ── Fallback in-memory dictionary mode ───────────────────────────────
        if not HAS_FAISS or self.index is None:
            scored = []
            for item_id in self.ids:
                if item_id in self._vectors:
                    score = _cosine_similarity(query_vector, self._vectors[item_id])
                    if score >= min_score:
                        scored.append({
                            "id": item_id,
                            "score": round(score, 4),
                            "metadata": self.metadata.get(item_id, {})
                        })
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:top_k]

        # ── FAISS mode ───────────────────────────────────────────────────────
        try:
            if len(query_vector) != self.dim:
                logger.warning("Search query dimension mismatch: expected %d, got %d", self.dim, len(query_vector))
                return []

            # Normalize query vector for Inner Product search
            q_np = np.array([query_vector], dtype=np.float32)
            q_norm = np.linalg.norm(q_np)
            if q_norm == 0:
                q_norm = 1.0
            normalized_q = q_np / q_norm

            # Search FAISS index
            scores, indices = self.index.search(normalized_q, min(top_k, len(self.ids)))
            
            scored = []
            for idx, score in zip(indices[0], scores[0]):
                if idx < 0 or idx >= len(self.ids):
                    continue
                item_id = self.ids[idx]
                # Cosine similarity for normalized vectors is score
                if score >= min_score:
                    scored.append({
                        "id": item_id,
                        "score": round(float(score), 4),
                        "metadata": self.metadata.get(item_id, {})
                    })
            
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored
        except Exception as e:
            logger.error("VectorStore search failed: %s", e)
            return []

    def delete(self, id: str) -> bool:
        """Removes a vector from the store. Returns True if found."""
        if id in self._vectors:
            self.ids.remove(id)
            del self._vectors[id]
            if id in self.metadata:
                del self.metadata[id]
            
            if HAS_FAISS:
                self._rebuild_index()
                self._save()
            return True
        return False

    def clear(self) -> None:
        """Wipes the entire store."""
        self._vectors.clear()
        self.metadata.clear()
        self.ids.clear()
        self.index = None
        self.dim = None
        
        if HAS_FAISS:
            self._save()

    def count(self) -> int:
        """Returns the number of stored vectors."""
        return len(self.ids)


# Singleton — shared across services in the same process
vector_store = VectorStore()

