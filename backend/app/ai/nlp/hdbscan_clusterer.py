"""
HDBSCAN Article Clusterer
==========================
Embeds news articles using a local sentence-transformer model and clusters
them into geopolitical "event topics" using HDBSCAN.

Design decisions (approved):
  - Runs as an HOURLY BACKGROUND BATCH PROCESS (not real-time per-article).
  - Uses 'all-MiniLM-L6-v2' (~80MB) — fast, CPU-friendly sentence embeddings.
  - HDBSCAN groups redundant/duplicate articles about the same breaking event
    into a single "event vector", reducing signal noise in the impact graph.

Usage (called from a scheduled background task):
    from app.ai.nlp.hdbscan_clusterer import hdbscan_clusterer
    clusters = hdbscan_clusterer.cluster(articles)
    # → list of EventCluster objects
"""

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

logger = logging.getLogger("geotrade.nlp.hdbscan_clusterer")


@dataclass
class EventCluster:
    """Represents a cluster of related news articles about a single event."""
    cluster_id:     int
    articles:       List[dict]          # list of raw article dicts
    centroid:       Optional[np.ndarray] = None  # mean embedding of the cluster
    representative: Optional[dict]       = None  # article closest to centroid
    label:          str = "unknown"      # most frequent NLI category in cluster


class HDBSCANClusterer:
    """
    Groups news articles into geopolitical event clusters.

    Primary:  sentence-transformers + HDBSCAN (local, CPU)
    Fallback: Returns each article as its own single-article cluster
              if models are unavailable.
    """

    MODEL_NAME     = "all-MiniLM-L6-v2"
    _encoder       = None
    _model_loaded  = False
    _model_failed  = False

    def _load_model(self):
        """Lazy-loads the sentence-transformer encoder on first call."""
        if self._model_loaded or self._model_failed:
            return
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading sentence-transformer: %s (CPU)...", self.MODEL_NAME)
            HDBSCANClusterer._encoder = SentenceTransformer(self.MODEL_NAME, device="cpu")
            HDBSCANClusterer._model_loaded = True
            logger.info("Sentence-transformer loaded successfully.")
        except Exception as exc:
            logger.warning(
                "Failed to load sentence-transformer (%s): %s. "
                "Clustering will return single-article clusters.",
                self.MODEL_NAME, exc,
            )
            HDBSCANClusterer._model_failed = True

    def cluster(
        self,
        articles: List[dict],
        min_cluster_size: int = 2,
        min_samples: int = 1,
    ) -> List[EventCluster]:
        """
        Embeds and clusters a batch of articles.

        Args:
            articles:         List of article dicts with 'headline' and 'summary' keys.
            min_cluster_size: Minimum number of articles to form a cluster (default 2).
            min_samples:      HDBSCAN min_samples parameter.

        Returns:
            List of EventCluster objects. Noise points (cluster_id = -1 in HDBSCAN)
            are returned as individual single-article clusters.
        """
        if not articles:
            return []

        if len(articles) < 2:
            return [EventCluster(cluster_id=0, articles=articles, representative=articles[0])]

        self._load_model()

        if self._model_loaded and self._encoder is not None:
            return self._hdbscan_cluster(articles, min_cluster_size, min_samples)

        # Fallback: each article is its own cluster
        return [
            EventCluster(cluster_id=i, articles=[art], representative=art)
            for i, art in enumerate(articles)
        ]

    def _hdbscan_cluster(
        self,
        articles: List[dict],
        min_cluster_size: int,
        min_samples: int,
    ) -> List[EventCluster]:
        """Core HDBSCAN clustering logic."""
        try:
            import hdbscan as hdbscan_lib

            # Build text strings for embedding
            texts = [
                f"{art.get('headline', '')} {art.get('summary', '')}".strip()
                for art in articles
            ]

            # Embed all texts at once (batch is faster)
            logger.info("Embedding %d articles for clustering...", len(texts))
            embeddings = self._encoder.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # Run HDBSCAN
            clusterer = hdbscan_lib.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric="euclidean",
                prediction_data=False,
            )
            labels = clusterer.fit_predict(embeddings)

            # Group articles by cluster label
            cluster_map: dict = {}
            for idx, label in enumerate(labels):
                cluster_map.setdefault(label, []).append(idx)

            event_clusters = []
            virtual_id = 0

            for label, indices in cluster_map.items():
                cluster_articles  = [articles[i] for i in indices]
                cluster_embeddings = embeddings[indices]
                centroid          = cluster_embeddings.mean(axis=0)

                # Find the article closest to the centroid (most representative)
                dists       = np.linalg.norm(cluster_embeddings - centroid, axis=1)
                rep_idx     = int(np.argmin(dists))
                representative = cluster_articles[rep_idx]

                if label == -1:
                    # Noise points: each becomes its own cluster
                    for art in cluster_articles:
                        event_clusters.append(EventCluster(
                            cluster_id=virtual_id,
                            articles=[art],
                            centroid=None,
                            representative=art,
                        ))
                        virtual_id += 1
                else:
                    event_clusters.append(EventCluster(
                        cluster_id=label,
                        articles=cluster_articles,
                        centroid=centroid,
                        representative=representative,
                    ))
                    virtual_id += 1

            logger.info(
                "Clustered %d articles into %d event clusters.",
                len(articles), len(event_clusters),
            )
            return event_clusters

        except Exception as exc:
            logger.warning("HDBSCAN clustering failed: %s. Returning individual clusters.", exc)
            return [
                EventCluster(cluster_id=i, articles=[art], representative=art)
                for i, art in enumerate(articles)
            ]

    def get_representative_articles(self, articles: List[dict]) -> List[dict]:
        """
        Convenience method: clusters articles and returns only the
        representative (most central) article from each cluster.
        Useful for deduplicating breaking news before signal routing.
        """
        clusters = self.cluster(articles)
        return [c.representative for c in clusters if c.representative is not None]


# Singleton instance
hdbscan_clusterer = HDBSCANClusterer()
