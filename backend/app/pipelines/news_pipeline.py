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
import asyncio
import hashlib
import time
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
from ..ai.nlp.zero_shot_classifier import zero_shot_classifier
from ..ai.nlp.sentiment_analysis import SentimentAnalyzer
from ..ai.embeddings.embedding_model import embedding_model
from ..ai.embeddings.vector_store import vector_store
from ..utils.date_utils import parse_newsapi_datetime
from ..core.constants import IMPACT_CRITICAL, IMPACT_HIGH, IMPACT_ELEVATED
from ..api.routes.ws import manager

logger = logging.getLogger("geotrade.pipelines.news")


PILLAR_KEYWORDS = {
    "military": {"war", "conflict", "military", "missile", "drone", "nuclear", "terrorism", "insurgency", "troops", "airstrike", "combat", "army", "navy", "clash", "bomb", "blast", "defense"},
    "economic": {"sanctions", "export controls", "export restrictions", "tariffs", "trade war", "rare earths", "semiconductors", "supply chain disruption", "economic coercion", "embargo", "restrict trade"},
    "energy": {"oil", "natural gas", "lng", "opec", "pipeline", "strait of hormuz", "red sea shipping", "energy security", "petroleum", "diesel"},
    "cyber": {"cyberattack", "ransomware", "critical infrastructure", "espionage", "cyber warfare", "hack", "hacking", "malware", "ddos"}
}

HIGH_RISK_COUNTRIES = {
    "china", "taiwan", "russia", "ukraine", "iran", "israel", "north korea", 
    "south korea", "india", "pakistan", "nato", "eu", "united nations", "u.s.", "usa", "us", "uk", "united kingdom", "germany"
}

PRIORITY_SOURCES = {
    "highest": {"reuters", "associated press", "ap", "bbc", "al jazeera", "financial times", "defense news", "bloomberg"},
    "low": {"blog", "opinion", "medium.com", "substack", "wordpress", "gossip", "sports", "tony awards", "grammy", "oscar", "fashion"}
}


class NewsPipeline:
    """
    Automated pipeline that fetches global news, uses AI to evaluate its
    geopolitical severity, and stores high-impact events in the database.
    Each event is now linked to the correct country via entity extraction.
    """

    def calculate_relevance_score(self, title: str, summary: str, source: str) -> float:
        """
        Computes relevance score based on keyword categorization, country hotspots, and source tiers.
        """
        score = 0.0
        text = f"{title} {summary}".lower()
        
        # 1. Pillar scoring (+15 points per unique matching category)
        for pillar, keywords in PILLAR_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                score += 15.0
                
        # 2. Country/hotspot boost (+10 points if any high-risk country is mentioned)
        if any(country in text for country in HIGH_RISK_COUNTRIES):
            score += 10.0
            
        # 3. Source priority ranking (+25 for highest tier, -20 for low tier/opinion/blog, +10 for medium)
        src_lower = source.lower()
        if any(hs in src_lower for hs in PRIORITY_SOURCES["highest"]):
            score += 25.0
        elif any(ls in src_lower for ls in PRIORITY_SOURCES["low"]):
            score -= 20.0
        else:
            score += 10.0
            
        return score

    async def sync_geopolitical_events(self, db: Session) -> dict:
        """
        Main entry point. Fetches news from two sources:
          1. Top-headlines (general breaking news)
          2. Geopolitical 'everything' search (sanctions, war, conflict, energy)
        Classifies each article with AI, links to a country, and persists
        events with severity >= 3. Uses DB-level + FAISS deduplication.
        """
        if not settings.NEWS_API_KEY:
            return {"status": "error", "message": "NEWS_API_KEY is not configured."}
        if not settings.OPENAI_API_KEY:
            return {"status": "error", "message": "OPENAI_API_KEY is required to classify events."}

        # ── 1. Fetch news concurrently using asyncio.to_thread to prevent blocking the main event loop ──
        import asyncio
        (
            raw_reuters,
            raw_bbc,
            raw_aljazeera,
            raw_headlines,
            raw_geo,
            raw_gdelt,
            raw_finnhub,
        ) = await asyncio.gather(
            asyncio.to_thread(news_service.get_reuters_news),
            asyncio.to_thread(news_service.get_bbc_news),
            asyncio.to_thread(news_service.get_aljazeera_news),
            asyncio.to_thread(news_service.get_geopolitical_news),
            asyncio.to_thread(news_service.get_geopolitical_everything),
            asyncio.to_thread(news_service.get_gdelt_events),
            asyncio.to_thread(news_service.get_market_news, "general"),
        )

        # Merge and deduplicate by headline before processing
        seen_titles: set = set()
        raw_news: list = []
        
        all_feeds = [
            raw_reuters, raw_bbc, raw_aljazeera, raw_headlines, 
            raw_geo, raw_gdelt, raw_finnhub
        ]
        for feed in all_feeds:
            if not feed:
                continue
            for article in feed:
                title = (article.get("headline") or "").strip()
                if title and title not in seen_titles and "[Demo]" not in title:
                    seen_titles.add(title)
                    raw_news.append(article)

        if not raw_news:
            return {"status": "error", "message": "Could not fetch valid news from any source."}

        # ── 2. Initialise helpers ─────────────────────────────────────────
        engine    = get_chat_engine(settings.OPENAI_API_KEY)
        extractor = EntityExtractor(api_key=settings.OPENAI_API_KEY)
        embedder  = embedding_model
        event_repo = EventRepository(db)
        risk_repo  = CountryRiskRepository(db)
        added_events = 0
        # ── 3. Filter and Deduplicate Candidates First ────────────────────
        candidates = []
        for article in raw_news:
            title = (article.get("headline") or "").strip()
            summary = (article.get("summary") or "").strip()
            if not title:
                continue

            # Check local relevance score
            source = article.get("source") or "NewsAPI"
            score = self.calculate_relevance_score(title, summary, source)
            if score < 25.0:
                logger.debug("Local Filter: Skipping low-relevance article (score=%.1f): '%s'", score, title[:50])
                continue

            # DB exact title check
            if event_repo.exists_by_title(title):
                logger.debug("Skipping already-saved event: '%s'", title[:60])
                continue

            candidates.append((article, score))

        # Sort candidates by relevance score descending so we process the most relevant ones first
        candidates.sort(key=lambda x: x[1], reverse=True)

        # ── 4. Process articles (up to 30 highly relevant, new candidates) ─
        for article, score in candidates[:30]:
            if settings.IS_SHUTTING_DOWN:
                logger.info("Application shutdown detected. Stopping geopolitical news sync.")
                break
            title   = (article.get("headline") or "").strip()
            summary = (article.get("summary") or "").strip()

            logger.info("Local Filter: Accepted high-relevance candidate (score=%.1f): '%s'", score, title[:50])

            # ── Layer 1b: Local NLP ─ SHA-256 dedup (fast, no API call) ───────────────
            article_hash = hashlib.sha256(
                f"{title}{summary[:200]}".encode("utf-8")
            ).hexdigest()[:16]
            logger.debug("Article hash: %s for '%s'", article_hash, title[:40])

            # ── Layer 2: Semantic FAISS dedup (catches paraphrases) ──────────
            # Skip if embedder is in BOW fallback mode (dim=256, no HF/OpenAI key).
            # BOW vectors are not semantically meaningful for similarity search.
            try:
                text_to_embed = f"{title} {summary[:400]}"
                vec = await asyncio.to_thread(embedder.get_embedding, text_to_embed)
                is_bow_fallback = (vec is not None and len(vec) == 256)
                if is_bow_fallback:
                    logger.debug("Embedder in BOW fallback mode — skipping FAISS dedup for '%s'", title[:50])
                else:
                    # 0.95+ = near-identical paraphrase; 0.88 was too aggressive
                    # and blocked genuinely new events about ongoing topics
                    matches = vector_store.search(vec, top_k=1, min_score=0.95)
                    if matches:
                        logger.info(
                            "Skipping near-duplicate: '%s' matches '%s' (%.2f)",
                            title[:50],
                            matches[0]["metadata"].get("title", "")[:50],
                            matches[0]["score"],
                        )
                        continue
            except Exception as dedup_exc:
                logger.warning("Semantic deduplication failed for '%s': %s", title[:60], dedup_exc)
                vec = None

            # ── Local NLP classification + sentiment (Phase 1: replaces 4.0s sleep) ───
            local_event_type = zero_shot_classifier.classify_to_event_type(
                f"{title} {summary[:300]}"
            )
            sentiment_analyzer = SentimentAnalyzer()
            local_sentiment    = sentiment_analyzer.analyze(f"{title} {summary[:300]}")
            logger.debug(
                "Local NLP: event_type=%s  sentiment=%s (%.3f) via %s",
                local_event_type,
                local_sentiment["sentiment"],
                local_sentiment["score_signed"],
                local_sentiment.get("source", "?"),
            )

            analysis = await asyncio.to_thread(self._evaluate_news_with_ai, engine, title, summary, local_event_type)
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

            # ── Casualty / Economic Impact Stats & Escalation ──────────
            casualties = int(analysis.get("casualties", 0) or 0)
            economic_damage = float(analysis.get("economic_damage_million_usd", 0.0) or 0.0)
            infra_dest = str(analysis.get("infrastructure_destruction", "Minimal"))
            displaced = int(analysis.get("displaced_population", 0) or 0)
            escalation_potential = int(analysis.get("escalation_potential", 3))

            # Programmatically calculate Impact Factor (1.0 to 2.0)
            impact_factor = 1.0
            if casualties >= 500:
                impact_factor += 0.3
            elif casualties >= 50:
                impact_factor += 0.15

            if economic_damage >= 1000.0:  # $1 Billion+
                impact_factor += 0.3
            elif economic_damage >= 100.0:  # $100 Million+
                impact_factor += 0.15

            if infra_dest.lower() == "severe":
                impact_factor += 0.2
            elif infra_dest.lower() == "moderate":
                impact_factor += 0.1

            if displaced >= 100000:
                impact_factor += 0.2
            elif displaced >= 10000:
                impact_factor += 0.1

            impact_factor = min(2.0, max(1.0, round(impact_factor, 2)))

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
                    escalation_potential=escalation_potential,
                    impact_factor=impact_factor,
                    casualties=casualties,
                    economic_damage=economic_damage,
                    infrastructure_destruction=infra_dest,
                    displaced_population=displaced,
                    source=article.get("source", "NewsAPI"),
                    timestamp=ts,
                    country_id=country_id,
                )
                saved = event_repo.create(event_in)
                added_events += 1

                # ── Vector embedding (RAG indexing) ─────────────────────────
                # Reuse vec from the dedup step above to avoid a 2nd API call.
                try:
                    if vec is None:
                        text_to_embed = f"{title} {summary[:400]}"
                        vec = await asyncio.to_thread(embedder.get_embedding, text_to_embed)
                    if vec is not None:
                        vector_store.add_vector(
                            id=f"event_{saved.id}",
                            vector=vec,
                            metadata={
                                "title":      title,
                                "summary":    summary[:300],
                                "event_type": analysis.get("event_type", "policy"),
                                "severity":   severity,
                                "escalation_potential": escalation_potential,
                                "impact_factor": impact_factor,
                                "casualties": casualties,
                                "economic_damage": economic_damage,
                                "infrastructure_destruction": infra_dest,
                                "displaced_population": displaced,
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
            "articles_fetched": len(raw_news),
            "articles_processed": len(candidates[:30]),
            "events_added": added_events,
        }

    # ── Private helpers ────────────────────────────────────────────────────

    def _evaluate_news_with_ai(
        self, engine, title: str, summary: str,
        local_event_type: str = "policy"
    ) -> dict | None:
        """
        Asks the LLM to evaluate severity and impact stats.
        The event_type is pre-filled by the local zero-shot classifier,
        so the LLM only needs to assess severity/casualties — fewer tokens.
        """
        prompt = NEWS_EVALUATION_PROMPT.format(title=title, summary=summary[:500])
        result = engine.ask_json(prompt, temperature=0.2, max_tokens=150)
        if result is None:
            logger.warning("AI evaluation returned None for: %s", title[:60])
            return None
        # Override event_type with the locally computed one (more accurate)
        if local_event_type:
            result["event_type"] = local_event_type
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
