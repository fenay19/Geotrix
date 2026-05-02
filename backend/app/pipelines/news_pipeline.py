"""
NewsPipeline: fetches global news, classifies geopolitical severity with AI,
links each event to a country via EntityExtractor, and persists to the DB.

Key fixes vs. original:
  - Uses ChatEngine instead of raw requests.post
  - Uses prompt_templates.NEWS_EVALUATION_PROMPT (no more inline string)
  - Uses parse_json_response from helpers (no more duplicated strip logic)
  - Uses EntityExtractor to resolve country_id (was always None before)
  - Uses parse_newsapi_datetime / impact labels from constants
  - Processes top 10 articles (was capped at 5)
"""

import logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..services.news_service import news_service
from ..repositories.event_repo import EventRepository
from ..repositories.risk_repo import CountryRiskRepository
from ..schemas.event_schema import EventCreate
from ..config import settings
from ..ai.chatbot.chat_engine import get_chat_engine
from ..ai.chatbot.prompt_templates import NEWS_EVALUATION_PROMPT
from ..ai.nlp.entity_extraction import EntityExtractor
from ..ai.embeddings.embedding_model import EmbeddingModel
from ..ai.embeddings.vector_store import vector_store
from ..utils.date_utils import parse_newsapi_datetime
from ..core.constants import IMPACT_CRITICAL, IMPACT_HIGH, IMPACT_ELEVATED
from ..api.routes.ws import manager

logger = logging.getLogger("geotrade.pipelines.news")


class NewsPipeline:
    """
    Automated pipeline that fetches global news, uses AI to evaluate its
    geopolitical severity, and stores high-impact events in the database.
    Each event is now linked to the correct country via entity extraction.
    """

    async def sync_geopolitical_events(self, db: Session) -> dict:
        """
        Main entry point. Fetches news, classifies each article, links it
        to a country, and persists events with severity >= 3.
        """
        if not settings.NEWS_API_KEY:
            return {"status": "error", "message": "NEWS_API_KEY is not configured."}
        if not settings.OPENAI_API_KEY:
            return {"status": "error", "message": "OPENAI_API_KEY is required to classify events."}

        # ── 1. Fetch raw news ──────────────────────────────────────────────
        raw_news = news_service.get_geopolitical_news()
        if not raw_news or "[Demo]" in raw_news[0].get("headline", ""):
            return {"status": "error", "message": "Could not fetch valid news."}

        # ── 2. Initialise helpers ─────────────────────────────────────────
        engine    = get_chat_engine(settings.OPENAI_API_KEY)
        extractor = EntityExtractor(api_key=settings.OPENAI_API_KEY)
        embedder  = EmbeddingModel(api_key=settings.OPENAI_API_KEY)
        event_repo = EventRepository(db)
        risk_repo  = CountryRiskRepository(db)
        added_events = 0

        # ── 3. Process articles (top 10) ──────────────────────────────────
        for article in raw_news[:10]:
            title   = article.get("headline", "")
            summary = article.get("summary", "")

            analysis = self._evaluate_news_with_ai(engine, title, summary)
            if not analysis:
                continue

            severity = analysis.get("severity", 0)
            if severity < 3:
                continue  # low-impact: skip to avoid cluttering DB

            # ── Severity → impact label ────────────────────────────────
            if severity >= 8:
                impact_label = IMPACT_CRITICAL
            elif severity >= 6:
                impact_label = IMPACT_HIGH
            else:
                impact_label = IMPACT_ELEVATED

            # ── Country resolution (the critical fix) ─────────────────
            country_id = self._resolve_country_id(extractor, risk_repo, title, summary)

            # ── Timestamp ─────────────────────────────────────────────
            ts = parse_newsapi_datetime(article.get("datetime", ""))

            try:
                event_in = EventCreate(
                    title=title,
                    description=summary,
                    event_type=analysis.get("event_type", "policy"),
                    severity=severity,
                    impact_label=impact_label,
                    source=article.get("source", "NewsAPI"),
                    timestamp=ts,
                    country_id=country_id,   # ← now properly populated
                )
                saved = event_repo.create(event_in)
                added_events += 1

                # ── Vector embedding (RAG indexing) ───────────────────────
                try:
                    text_to_embed = f"{title} {summary[:400]}"
                    vec = embedder.get_embedding(text_to_embed)
                    vector_store.add_vector(
                        id=f"event_{saved.id}",
                        vector=vec,
                        metadata={
                            "title":      title,
                            "summary":    summary[:300],
                            "event_type": analysis.get("event_type", "policy"),
                            "severity":   severity,
                            "country_id": country_id,
                        },
                    )
                    logger.debug("Embedded event_%d into vector store.", saved.id)
                except Exception as embed_exc:
                    logger.warning("Failed to embed event '%s': %s", title[:60], embed_exc)

                logger.info(
                    "Saved event: '%s' (severity=%d, country_id=%s)",
                    title[:60], severity, country_id,
                )
            except Exception as exc:
                logger.error("Failed to save event '%s': %s", title[:60], exc)

        return {
            "status": "success",
            "articles_processed": len(raw_news[:10]),
            "events_added": added_events,
        }

    # ── Private helpers ────────────────────────────────────────────────────

    def _evaluate_news_with_ai(self, engine, title: str, summary: str) -> dict | None:
        """
        Asks OpenAI to classify a news snippet for severity and event_type.
        Uses the centralized prompt template and ChatEngine.
        """
        prompt = NEWS_EVALUATION_PROMPT.format(title=title, summary=summary[:500])
        result = engine.ask_json(prompt, temperature=0.2, max_tokens=150)
        if result is None:
            logger.warning("AI evaluation returned None for: %s", title[:60])
        return result

    def _resolve_country_id(
        self, extractor: EntityExtractor, risk_repo, title: str, summary: str
    ) -> int | None:
        """
        Uses EntityExtractor to get a country_code, then looks up its DB row.
        Returns the country's integer PK or None if not found.
        """
        try:
            country_code, country_name = extractor.extract_country(title, summary)
            if not country_code:
                return None

            # Look up the CountryRisk row by ISO code
            country = risk_repo.get_by_code(country_code)
            if country:
                logger.debug("Resolved '%s' → country_id=%d", country_code, country.id)
                return country.id

            logger.debug("Country code '%s' not in DB yet.", country_code)
        except Exception as exc:
            logger.warning("Country resolution failed: %s", exc)
        return None


news_pipeline = NewsPipeline()
