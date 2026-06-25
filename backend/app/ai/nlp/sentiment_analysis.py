"""
Sentiment analysis for financial and geopolitical text.

Upgraded (Phase 1):
  PRIMARY:   Local VADER SentimentIntensityAnalyzer — sub-1ms, CPU-only, $0 cost.
  SECONDARY: OpenAI API — only used if api_key is provided AND VADER is unavailable.
  FALLBACK:  Lightweight keyword rules (original fallback).
"""

import logging
from typing import Optional

from ...utils.api_clients import api_client
from ...utils.helpers import parse_json_response
from ...core.constants import DEFAULT_AI_MODEL, OPENAI_API_URL
from ..chatbot.prompt_templates import SENTIMENT_ANALYSIS_PROMPT

logger = logging.getLogger("geotrade.nlp.sentiment")

# ── VADER lazy loader ─────────────────────────────────────────────────────────
_vader_analyzer = None
_vader_failed   = False


def _get_vader():
    """Lazy-loads and caches the VADER SentimentIntensityAnalyzer."""
    global _vader_analyzer, _vader_failed
    if _vader_analyzer is not None or _vader_failed:
        return _vader_analyzer
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        _vader_analyzer = SentimentIntensityAnalyzer()
        logger.info("VADER SentimentIntensityAnalyzer loaded (CPU).")
    except Exception as exc:
        logger.warning("VADER not available: %s. Falling back to keyword rules.", exc)
        _vader_failed = True
    return _vader_analyzer

_POSITIVE = {
    "ceasefire", "peace", "agreement", "deal", "recovery", "growth",
    "stabilize", "calm", "resolved", "diplomatic", "negotiation", "surplus",
}
_NEGATIVE = {
    "war", "conflict", "invasion", "attack", "sanction", "crisis",
    "collapse", "tension", "threat", "escalat", "bomb", "strike",
    "terror", "missile", "casualt", "recession", "deficit", "default",
}


class SentimentAnalyzer:
    """
    Classifies text sentiment as positive / negative / neutral with a
    confidence score and a market-tone tag (risk-on / risk-off / neutral).

    Output contract (all methods):
        {
            "sentiment":    "positive" | "negative" | "neutral",
            "score":        float 0-1,          # magnitude of sentiment
            "score_signed": float -1 to +1,     # signed: + for positive, - for negative
            "market_tone":  "risk-on" | "risk-off" | "neutral"
        }

    score_signed is the key feature consumed by the Stage 2 ML model.
    It encodes both direction and magnitude in a single float, which
    XGBoost can use directly as a numerical input feature.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def analyze(self, text: str) -> dict:
        """
        Returns:
            {
                "sentiment":    "positive" | "negative" | "neutral",
                "score":        float 0-1,
                "score_signed": float -1 to +1,
                "market_tone":  "risk-on" | "risk-off" | "neutral",
                "source":       "vader" | "openai" | "keyword-rules"
            }
        """
        # 1. Try VADER first (local, free, fast)
        vader = _get_vader()
        if vader is not None:
            return self._vader_analyze(text, vader)

        # 2. Try OpenAI if api_key is set (secondary)
        if self.api_key:
            result = self._openai_analyze(text)
            if result:
                r = self._attach_signed_score(result)
                r["source"] = "openai"
                return r

        # 3. Keyword fallback
        return self._keyword_analyze(text)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _vader_analyze(self, text: str, vader) -> dict:
        """Runs VADER and maps compound score to the standard output contract."""
        scores  = vader.polarity_scores(text[:1000])
        compound = scores["compound"]   # -1.0 to +1.0

        if compound >= 0.05:
            sentiment  = "positive"
            market_tone = "risk-on"
            score      = round(compound, 4)
        elif compound <= -0.05:
            sentiment  = "negative"
            market_tone = "risk-off"
            score      = round(abs(compound), 4)
        else:
            sentiment  = "neutral"
            market_tone = "neutral"
            score      = round(abs(compound), 4)

        return {
            "sentiment":    sentiment,
            "score":        score,
            "score_signed": round(compound, 4),
            "market_tone":  market_tone,
            "source":       "vader",
        }

    def _openai_analyze(self, text: str) -> Optional[dict]:
        prompt = SENTIMENT_ANALYSIS_PROMPT.format(text=text[:800])
        try:
            resp = api_client.post_data(
                OPENAI_API_URL,
                json={
                    "model": DEFAULT_AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 80,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            content = resp["choices"][0]["message"]["content"]
            return parse_json_response(content)
        except Exception as exc:
            logger.warning("SentimentAnalyzer._openai_analyze failed: %s", exc)
            return None

    def _keyword_analyze(self, text: str) -> dict:
        """Lightweight fallback using keyword counts. Includes score_signed and source."""
        lower = text.lower()
        pos = sum(1 for w in _POSITIVE if w in lower)
        neg = sum(1 for w in _NEGATIVE if w in lower)
        total = pos + neg or 1
        if neg > pos:
            score = round(neg / total, 2)
            return {
                "sentiment":    "negative",
                "score":        score,
                "score_signed": -score,
                "market_tone":  "risk-off",
                "source":       "keyword-rules",
            }
        if pos > neg:
            score = round(pos / total, 2)
            return {
                "sentiment":    "positive",
                "score":        score,
                "score_signed": +score,
                "market_tone":  "risk-on",
                "source":       "keyword-rules",
            }
        return {
            "sentiment":    "neutral",
            "score":        0.5,
            "score_signed": 0.0,
            "market_tone":  "neutral",
            "source":       "keyword-rules",
        }

    @staticmethod
    def _attach_signed_score(result: dict) -> dict:
        """
        Attaches score_signed to an OpenAI result dict.
        OpenAI returns 'score' as a magnitude (0-1) and 'sentiment' as direction.
        We combine them here.
        """
        sentiment = result.get("sentiment", "neutral")
        score     = float(result.get("score", 0.5))

        if sentiment == "positive":
            signed = +score
        elif sentiment == "negative":
            signed = -score
        else:
            signed = 0.0

        result["score_signed"] = round(signed, 4)
        return result
