import json
import requests
from sqlalchemy.orm import Session
from ..services.risk_service import risk_service
from ..services.gti_service import gti_service
from ..config import settings

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class RiskPipeline:
    """
    Orchestration pipeline that recalculates geopolitical risk scores for
    all countries and refreshes the Global Tension Index (GTI).

    This pipeline should run AFTER the NewsPipeline so it can factor in
    the latest AI-evaluated events that were just inserted into the database.
    """

    def sync_global_risk(self, db: Session, include_ai_summary: bool = True) -> dict:
        """
        Recalculates risk for every country and refreshes the GTI.

        Steps:
            1. Fetch all countries from CountryRisk table.
            2. Recalculate each country's risk score from its recent Events.
            3. Recalculate (and persist) the global GTI score.
            4. Optionally generate an AI threat-level summary paragraph.

        Args:
            db:                 SQLAlchemy session.
            include_ai_summary: If True and OPENAI_API_KEY is set, generate
                                a qualitative global threat summary.

        Returns:
            Summary dict with updated country count, new GTI, and summary text.
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
                    if updated_country.risk_score >= 65:
                        high_risk_countries.append({
                            "code": updated_country.country_code,
                            "name": updated_country.country_name,
                            "score": updated_country.risk_score,
                            "color": updated_country.color_code,
                        })
            except Exception as e:
                print(f"[WARN] Failed to recalculate risk for {country.country_code}: {e}")

        # ── 2. Recalculate & persist the global GTI ─────────────────────────
        try:
            new_gti = gti_service.calculate_current_gti(db)
        except Exception as e:
            print(f"[ERROR] GTI recalculation failed: {e}")
            new_gti = None

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

    def _generate_threat_summary(self, gti: float, high_risk_countries: list) -> str:
        """
        Asks OpenAI to produce a 2-3 sentence qualitative summary of the
        current global threat landscape, given the top high-risk countries
        and the current GTI score.
        """
        country_list = ", ".join(
            f"{c['name']} ({c['code']}, score: {c['score']})"
            for c in sorted(high_risk_countries, key=lambda x: x["score"], reverse=True)[:5]
        )

        prompt = f"""You are a senior geopolitical risk analyst for a financial intelligence platform.

Current Global Tension Index (GTI): {gti}/100
Highest risk countries right now: {country_list}

Write a precise, professional 2-3 sentence summary of the current global threat landscape for traders and investors.
Do NOT use bullet points. Do NOT use markdown. Write in plain text only."""

        try:
            resp = requests.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 200,
                },
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"[WARN] AI threat summary failed: {e}")
            return None


risk_pipeline = RiskPipeline()
