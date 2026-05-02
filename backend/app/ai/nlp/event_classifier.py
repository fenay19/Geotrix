"""
Event classifier: maps raw news text to one of the canonical GeoTrade event types.
Valid types: war, conflict, sanctions, economic, policy, unrest
"""

import logging
from typing import Optional

from ...utils.api_clients import api_client
from ...utils.helpers import parse_json_response
from ...core.constants import DEFAULT_AI_MODEL, OPENAI_API_URL, EVENT_TYPES

logger = logging.getLogger("geotrade.nlp.event_classifier")

# Keyword → event_type mapping for the free fallback
_KEYWORD_RULES = {
    "war":       ["war", "warfare", "military operation", "combat", "airstrike"],
    "conflict":  ["conflict", "clash", "fight", "battle", "skirmish", "troops"],
    "sanctions": ["sanction", "embargo", "ban", "restriction", "freeze assets"],
    "unrest":    ["protest", "riot", "demonstration", "uprising", "coup", "unrest"],
    "economic":  ["recession", "inflation", "gdp", "trade deficit", "debt", "tariff", "market crash"],
    "policy":    ["policy", "legislation", "election", "government", "treaty", "agreement", "accord"],
}

_CLASSIFY_PROMPT = """\
Classify the following news into exactly one of these geopolitical event types:
war, conflict, sanctions, economic, policy, unrest

Title: {title}
Summary: {summary}

Respond ONLY with a valid JSON object (no markdown):
{{"event_type": "<one of: war, conflict, sanctions, economic, policy, unrest>"}}"""


class EventClassifier:
    """
    Classifies a news headline + summary into a canonical event_type.
    Uses keyword rules first (free), falls back to OpenAI when ambiguous.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def classify(self, text: str) -> str:
        """
        Legacy single-string interface.
        Returns one of EVENT_TYPES, defaults to "policy" if uncertain.
        """
        return self.classify_news("", text)

    def classify_news(self, title: str, summary: str) -> str:
        """
        Classifies a news event. Returns one of: war, conflict, sanctions,
        economic, policy, unrest.
        """
        combined = f"{title} {summary}".lower()

        # Step 1: keyword rules (free)
        scores = {etype: 0 for etype in EVENT_TYPES}
        for etype, keywords in _KEYWORD_RULES.items():
            scores[etype] = sum(1 for kw in keywords if kw in combined)

        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best

        # Step 2: OpenAI fallback
        if self.api_key:
            result = self._openai_classify(title, summary)
            if result:
                return result

        return "policy"  # neutral default

    def _openai_classify(self, title: str, summary: str) -> Optional[str]:
        prompt = _CLASSIFY_PROMPT.format(title=title, summary=summary[:400])
        try:
            resp = api_client.post_data(
                OPENAI_API_URL,
                json={
                    "model": DEFAULT_AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 30,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            content = resp["choices"][0]["message"]["content"]
            result = parse_json_response(content)
            if result:
                etype = result.get("event_type", "").lower()
                if etype in EVENT_TYPES:
                    return etype
        except Exception as exc:
            logger.warning("EventClassifier._openai_classify failed: %s", exc)
        return None
