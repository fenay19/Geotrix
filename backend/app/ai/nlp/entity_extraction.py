"""
Entity extraction: identifies the primary country mentioned in a news snippet.
This is the missing link that lets news_pipeline set country_id on events,
which in turn drives country-level risk recalculation.

Strategy (cheapest-first):
  1. Fast keyword scan (no API cost, covers ~20 most-mentioned countries).
  2. OpenAI fallback for anything ambiguous or not in the keyword map.
"""

import logging
from typing import Optional, Tuple

from ...utils.api_clients import api_client
from ...utils.helpers import parse_json_response
from ...core.constants import DEFAULT_AI_MODEL, OPENAI_API_URL
from ..chatbot.prompt_templates import ENTITY_EXTRACTION_PROMPT

logger = logging.getLogger("geotrade.nlp.entity_extraction")


class EntityExtractor:
    """
    Extracts the primary affected country from a news headline + summary.
    Returns (country_code, country_name) or (None, None).
    """

    # Fast keyword lookup — covers most geopolitically significant countries
    KEYWORD_MAP = {
        "russia":        ("RU", "Russia"),
        "ukraine":       ("UA", "Ukraine"),
        "china":         ("CN", "China"),
        "taiwan":        ("TW", "Taiwan"),
        "united states": ("US", "United States"),
        " usa ":         ("US", "United States"),
        "iran":          ("IR", "Iran"),
        "israel":        ("IL", "Israel"),
        "palestine":     ("PS", "Palestine"),
        "north korea":   ("KP", "North Korea"),
        "south korea":   ("KR", "South Korea"),
        "india":         ("IN", "India"),
        "pakistan":      ("PK", "Pakistan"),
        "saudi arabia":  ("SA", "Saudi Arabia"),
        "turkey":        ("TR", "Turkey"),
        "germany":       ("DE", "Germany"),
        "france":        ("FR", "France"),
        "britain":       ("GB", "United Kingdom"),
        "brazil":        ("BR", "Brazil"),
        "venezuela":     ("VE", "Venezuela"),
        "myanmar":       ("MM", "Myanmar"),
        "ethiopia":      ("ET", "Ethiopia"),
        "sudan":         ("SD", "Sudan"),
        "afghanistan":   ("AF", "Afghanistan"),
        "syria":         ("SY", "Syria"),
        "iraq":          ("IQ", "Iraq"),
        "japan":         ("JP", "Japan"),
        "indonesia":     ("ID", "Indonesia"),
        "mexico":        ("MX", "Mexico"),
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def extract(self, text: str) -> list:
        """
        Legacy list-style interface for backward compatibility.
        Prefer extract_country() for new code.
        """
        code, name = self.extract_country("", text)
        if code:
            return [{"entity": name, "type": "GPE", "country_code": code}]
        return []

    def extract_country(
        self, title: str, summary: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Identifies the primary country affected by a news event.
        Returns (country_code, country_name) e.g. ("RU", "Russia") or (None, None).
        """
        combined = f"{title} {summary}".lower()

        # Step 1: keyword pre-screening (free, fast)
        for keyword, (code, name) in self.KEYWORD_MAP.items():
            if keyword in combined:
                return code, name

        # Step 2: OpenAI fallback
        if self.api_key:
            return self._openai_extract(title, summary)

        return None, None

    def _openai_extract(
        self, title: str, summary: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """Uses OpenAI to extract the primary country from a news snippet."""
        prompt = ENTITY_EXTRACTION_PROMPT.format(title=title, summary=summary)
        try:
            resp = api_client.post_data(
                OPENAI_API_URL,
                json={
                    "model": DEFAULT_AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 80,
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
                code = result.get("country_code")
                name = result.get("country_name")
                if code and str(code).lower() not in ("null", "none", ""):
                    return code.upper(), name
        except Exception as exc:
            logger.warning("EntityExtractor._openai_extract failed: %s", exc)

        return None, None
