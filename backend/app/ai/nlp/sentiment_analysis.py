"""
Sentiment analysis for financial and geopolitical text.
Uses OpenAI for structured, finance-aware sentiment (risk-on / risk-off).
Falls back to a lightweight keyword approach if the API key is unavailable.
"""

import logging
from typing import Optional

from ...utils.api_clients import api_client
from ...utils.helpers import parse_json_response
from ...core.constants import DEFAULT_AI_MODEL, OPENAI_API_URL
from ..chatbot.prompt_templates import SENTIMENT_ANALYSIS_PROMPT

logger = logging.getLogger("geotrade.nlp.sentiment")

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
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def analyze(self, text: str) -> dict:
        """
        Returns:
            {
                "sentiment":    "positive" | "negative" | "neutral",
                "score":        float 0-1,
                "market_tone":  "risk-on" | "risk-off" | "neutral"
            }
        """
        if self.api_key:
            result = self._openai_analyze(text)
            if result:
                return result
        return self._keyword_analyze(text)

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
        """Lightweight fallback using keyword counts."""
        lower = text.lower()
        pos = sum(1 for w in _POSITIVE if w in lower)
        neg = sum(1 for w in _NEGATIVE if w in lower)
        total = pos + neg or 1
        if neg > pos:
            return {"sentiment": "negative", "score": round(neg / total, 2), "market_tone": "risk-off"}
        if pos > neg:
            return {"sentiment": "positive", "score": round(pos / total, 2), "market_tone": "risk-on"}
        return {"sentiment": "neutral", "score": 0.5, "market_tone": "neutral"}
