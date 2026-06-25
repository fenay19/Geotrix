"""
Market reasoner: produces a structured market outlook from geopolitical context.
Used by signal_service as a reasoning layer before generating trade signals.
"""

import logging
from typing import Optional

from ...utils.api_clients import api_client
from ...utils.helpers import parse_json_response
from ...core.constants import DEFAULT_AI_MODEL, OPENAI_API_URL
from ..chatbot.prompt_templates import MARKET_REASONING_PROMPT

logger = logging.getLogger("geotrade.reasoning.market_reasoner")


class MarketReasoner:
    """
    Produces a structured market outlook dict given live geopolitical context.
    Primary: OpenAI. Fallback: GTI-based heuristic rules.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def reason(self, context: dict) -> dict:
        """
        Args:
            context: {
                symbol, category, price, gti_score,
                country_score, top_events (list of event dicts)
            }
        Returns:
            {
                "direction":    "BULLISH" | "BEARISH" | "NEUTRAL",
                "confidence":   float 0-1,
                "key_drivers":  list[str],
                "summary":      str
            }
        """
        if self.api_key:
            result = self._openai_reason(context)
            if result:
                return result
        return self._heuristic_reason(context)

    def _openai_reason(self, context: dict) -> Optional[dict]:
        events = context.get("top_events", [])
        event_lines = "\n".join(
            f"- {e.get('title', '')} (Severity {e.get('severity', 5)}/10)"
            for e in events
        ) or "None"

        prompt = MARKET_REASONING_PROMPT.format(
            symbol=context.get("symbol", "Unknown"),
            category=context.get("category", "Unknown"),
            price=context.get("price", 0),
            gti_score=context.get("gti_score", 50),
            country_score=context.get("country_score", 50),
            event_lines=event_lines,
        )
        try:
            resp = api_client.post_data(
                OPENAI_API_URL,
                json={
                    "model": DEFAULT_AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 300,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=20,
            )
            content = resp["choices"][0]["message"]["content"]
            return parse_json_response(content)
        except Exception as exc:
            logger.warning("MarketReasoner._openai_reason failed: %s", exc)
            return None

    def _heuristic_reason(self, context: dict) -> dict:
        gti = context.get("gti_score", 50)
        country = context.get("country_score", 50)
        combined = gti * 0.6 + country * 0.4

        if combined > 65:
            return {
                "direction": "BEARISH",
                "confidence": round(min(0.9, combined / 100), 2),
                "key_drivers": ["High GTI reading", "Elevated country risk", "Risk-off sentiment"],
                "summary": f"Geopolitical risk is elevated (combined score {combined:.1f}/100). Markets are likely to adopt risk-off positioning.",
            }
        if combined < 35:
            return {
                "direction": "BULLISH",
                "confidence": round(min(0.85, (100 - combined) / 100), 2),
                "key_drivers": ["Low geopolitical tension", "Stable macro environment", "Risk-on sentiment"],
                "summary": f"Geopolitical risk is low (combined score {combined:.1f}/100). Conditions support risk-on positioning.",
            }
        return {
            "direction": "NEUTRAL",
            "confidence": 0.55,
            "key_drivers": ["Moderate geopolitical tension", "Mixed signals"],
            "summary": f"Geopolitical risk is moderate (combined score {combined:.1f}/100). No strong directional bias.",
        }


market_reasoner = MarketReasoner()

