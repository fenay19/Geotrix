"""
RiskPipeline: recalculates country risk scores and the Global Tension Index (GTI).

Refactored vs. original:
  - Uses ChatEngine instead of raw requests.post
  - Uses THREAT_SUMMARY_PROMPT from prompt_templates
  - Uses logger instead of print() statements
  - HIGH_RISK_THRESHOLD from constants (was hardcoded 65)
"""

import logging
from sqlalchemy.orm import Session

from ..services.risk_service import risk_service
from ..services.gti_service import gti_service
from ..config import settings
from ..ai.chatbot.chat_engine import get_chat_engine
from ..ai.chatbot.prompt_templates import THREAT_SUMMARY_PROMPT
from ..core.constants import HIGH_RISK_THRESHOLD

logger = logging.getLogger("geotrade.pipelines.risk")


class RiskPipeline:
    """
    Orchestration pipeline that recalculates geopolitical risk scores for
    all countries and refreshes the Global Tension Index (GTI).

    Run AFTER NewsPipeline so it can factor in the latest evaluated events.
    """

    def sync_global_risk(self, db: Session, include_ai_summary: bool = True) -> dict:
        """
        Recalculates risk for every country and refreshes the GTI.

        Steps:
            1. Fetch all countries from CountryRisk table.
            2. Recalculate each country's risk score from its recent Events.
            3. Recalculate (and persist) the global GTI score.
            4. Optionally generate an AI threat-level summary paragraph.
        """
        countries = risk_service.get_all_country_risks(db)

        if not countries:
            return {
                "status": "warning",
                "message": "No country risk records found. Seed the DB first.",
                "countries_updated": 0,
                "new_gti": None,
                "ai_summary": None,
            }

        # ── 1. Recalculate per-country risk scores ──────────────────────────
        updated = 0
        high_risk_countries = []

        for country in countries:
            try:
                updated_country = risk_service.recalculate_country_risk(db, country.country_code)
                if updated_country:
                    updated += 1
                    if updated_country.risk_score >= HIGH_RISK_THRESHOLD:
                        high_risk_countries.append({
                            "code":  updated_country.country_code,
                            "name":  updated_country.country_name,
                            "score": updated_country.risk_score,
                            "color": updated_country.color_code,
                        })
            except Exception as exc:
                logger.warning("Failed to recalculate risk for %s: %s", country.country_code, exc)

        logger.info("Risk recalculated for %d countries (%d high-risk).", updated, len(high_risk_countries))

        # ── 2. Recalculate & persist the global GTI ─────────────────────────
        new_gti = None
        try:
            new_gti = gti_service.calculate_current_gti(db)
            logger.info("New GTI score: %.1f", new_gti or 0)
        except Exception as exc:
            logger.error("GTI recalculation failed: %s", exc)

        # ── 3. Optional AI threat-level summary ─────────────────────────────
        ai_summary = None
        if include_ai_summary and settings.OPENAI_API_KEY and high_risk_countries:
            ai_summary = self._generate_threat_summary(new_gti, high_risk_countries)

        return {
            "status": "success",
            "countries_updated": updated,
            "high_risk_count": len(high_risk_countries),
            "new_gti": new_gti,
            "gti_label": gti_service.get_severity_label(new_gti) if new_gti is not None else None,
            "ai_summary": ai_summary,
        }

    def _generate_threat_summary(self, gti: float, high_risk_countries: list) -> str | None:
        """
        Uses ChatEngine to produce a 2-3 sentence qualitative summary of the
        current global threat landscape for the /risk/sync response.
        """
        country_list = ", ".join(
            f"{c['name']} ({c['code']}, score: {c['score']})"
            for c in sorted(high_risk_countries, key=lambda x: x["score"], reverse=True)[:5]
        )

        prompt = THREAT_SUMMARY_PROMPT.format(
            gti=round(gti or 0, 1),
            country_list=country_list,
        )

        engine = get_chat_engine(settings.OPENAI_API_KEY)
        result = engine.ask(prompt, temperature=0.4, max_tokens=200)
        if result:
            return result.strip()
        logger.warning("AI threat summary returned None — using fallback.")
        return f"Global tension is currently at {gti or 0:.1f}/100 with elevated risk in {country_list}."


risk_pipeline = RiskPipeline()
