"""
Event impact model: estimates the market impact of a geopolitical event.
This bridges the gap between raw events and trading signal generation.
"""

import logging
from typing import Optional

from ...utils.api_clients import api_client
from ...utils.helpers import parse_json_response
from ...core.constants import DEFAULT_AI_MODEL, OPENAI_API_URL
from ..chatbot.prompt_templates import EVENT_IMPACT_PROMPT

logger = logging.getLogger("geotrade.reasoning.event_impact")

# Rule-based fallback lookup (event_type → typical impact)
_IMPACT_RULES = {
    "war":       {"impact_score": 0.90, "direction": "DOWN", "affected_sectors": ["Energy", "Defense", "Finance"], "affected_assets": ["GOLD", "OIL_BRENT"]},
    "conflict":  {"impact_score": 0.75, "direction": "DOWN", "affected_sectors": ["Energy", "Defense"],            "affected_assets": ["GOLD", "OIL_BRENT"]},
    "sanctions": {"impact_score": 0.70, "direction": "DOWN", "affected_sectors": ["Finance", "Energy"],            "affected_assets": ["GOLD", "BTCUSD"]},
    "unrest":    {"impact_score": 0.60, "direction": "DOWN", "affected_sectors": ["Finance", "Consumer"],          "affected_assets": ["GOLD", "SP500"]},
    "economic":  {"impact_score": 0.65, "direction": "DOWN", "affected_sectors": ["Finance", "Tech"],              "affected_assets": ["SP500", "BTCUSD"]},
    "policy":    {"impact_score": 0.40, "direction": "NEUTRAL", "affected_sectors": ["Finance"],                   "affected_assets": ["SP500"]},
}


class EventImpactModel:
    """
    Estimates the market impact of a geopolitical event.
    Primary: OpenAI reasoning. Fallback: rule-based lookup.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def estimate_impact(self, event: dict) -> dict:
        """
        Args:
            event: dict with keys: title, event_type, severity, country_name

        Returns:
            {
                "impact_score":      float 0-1,
                "direction":         "UP" | "DOWN" | "NEUTRAL",
                "affected_sectors":  list[str],
                "affected_assets":   list[str],
                "reasoning":         str
            }
        """
        if self.api_key:
            result = self._openai_estimate(event)
            if result:
                return result
        return self._rule_based_estimate(event)

    def _openai_estimate(self, event: dict) -> Optional[dict]:
        prompt = EVENT_IMPACT_PROMPT.format(
            title=event.get("title", "Unknown"),
            event_type=event.get("event_type", "policy"),
            severity=event.get("severity", 5),
            country_name=event.get("country_name", "Unknown"),
        )
        try:
            resp = api_client.post_data(
                OPENAI_API_URL,
                json={
                    "model": DEFAULT_AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 200,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            content = resp["choices"][0]["message"]["content"]
            return parse_json_response(content)
        except Exception as exc:
            logger.warning("EventImpactModel._openai_estimate failed: %s", exc)
            return None

    def _rule_based_estimate(self, event: dict) -> dict:
        etype = (event.get("event_type") or "policy").lower()
        severity = event.get("severity", 5)
        base = _IMPACT_RULES.get(etype, _IMPACT_RULES["policy"]).copy()
        # Scale impact_score by severity
        base["impact_score"] = round(min(1.0, base["impact_score"] * (severity / 10) * 1.2), 2)
        base["reasoning"] = f"Rule-based estimate for a {etype} event with severity {severity}/10."
        return base
