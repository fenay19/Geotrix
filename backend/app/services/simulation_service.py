import requests
import json
from typing import Optional, List
from sqlalchemy.orm import Session
from ..repositories.simulation_repo import SimulationRepository
from ..repositories.risk_repo import GTIRepository
from ..repositories.event_repo import EventRepository
from ..schemas.simulation_schema import SimulationRunCreate
from ..config import settings

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Predefined impact templates for the rule-based fallback.
# Maps (event_type, magnitude) → asset impact percentages.
IMPACT_TEMPLATES = {
    ("war", "Severe"):      {"GOLD": +12, "OIL_BRENT": +18, "SP500": -15, "BTCUSD": -10},
    ("war", "Moderate"):    {"GOLD": +7,  "OIL_BRENT": +10, "SP500": -8,  "BTCUSD": -5},
    ("sanctions", "Severe"):{"GOLD": +8,  "OIL_BRENT": +12, "SP500": -10, "BTCUSD": -8},
    ("economic", "Severe"): {"GOLD": +5,  "OIL_BRENT": -8,  "SP500": -12, "BTCUSD": -15},
    ("policy", "Moderate"): {"GOLD": +3,  "OIL_BRENT": +2,  "SP500": -5,  "BTCUSD": -3},
}


class SimulationService:

    def get_simulations(self, db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 50):
        repo = SimulationRepository(db)
        return repo.get_all(user_id=user_id, skip=skip, limit=limit)

    def get_simulation(self, db: Session, run_id: int):
        repo = SimulationRepository(db)
        return repo.get_by_id(run_id)

    def create_simulation(self, db: Session, sim_in: SimulationRunCreate):
        repo = SimulationRepository(db)
        return repo.create(sim_in)

    # ── AI-Powered Simulation ───────────────────────────────────────────────

    def run_scenario(
        self,
        db: Session,
        scenario_name: str,
        region: str,
        event_type: str,
        magnitude: str,
        user_id: Optional[int] = None,
    ):
        """
        Main entry point: runs a geopolitical scenario simulation.
        1. PRIMARY: Uses OpenAI to reason about market impacts.
        2. FALLBACK: Uses a pre-defined impact template table.
        Saves the result to the DB and returns the SimulationRun.
        """
        # Gather context
        gti = GTIRepository(db).get_latest()
        gti_score = gti.current_score if gti else 50.0
        top_events = EventRepository(db).get_high_severity(min_severity=6)[:3]

        results = self._ai_simulate(scenario_name, region, event_type, magnitude, gti_score, top_events)
        if not results:
            results = self._rule_based_simulate(event_type, magnitude, region)

        sim_in = SimulationRunCreate(
            scenario_name=scenario_name,
            region=region,
            event_type=event_type,
            magnitude=magnitude,
            results=results,
            user_id=user_id,
        )
        return SimulationRepository(db).create(sim_in)

    def _ai_simulate(
        self,
        scenario_name: str,
        region: str,
        event_type: str,
        magnitude: str,
        gti_score: float,
        top_events: list,
    ) -> Optional[dict]:
        """Calls OpenAI to predict market impacts for a geopolitical scenario."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return None

        event_lines = "\n".join(
            f"- {e.title} (Severity {e.severity}/10)" for e in top_events
        ) if top_events else "None"

        prompt = f"""You are a quantitative geopolitical risk analyst.

Simulate the market impact of the following scenario and return ONLY a valid JSON object.

Scenario: {scenario_name}
Region: {region}
Event Type: {event_type}
Magnitude: {magnitude}
Current Global Tension Index (GTI): {gti_score}/100
Active Background Risks:
{event_lines}

Return ONLY this JSON structure (no markdown, no extra text):
{{
  "summary": "<2-3 sentence impact summary>",
  "affected_assets": {{
    "GOLD":     {{"impact_pct": <float>, "direction": "UP"|"DOWN"|"NEUTRAL", "reason": "<brief>"}},
    "OIL_BRENT":{{"impact_pct": <float>, "direction": "UP"|"DOWN"|"NEUTRAL", "reason": "<brief>"}},
    "SP500":    {{"impact_pct": <float>, "direction": "UP"|"DOWN"|"NEUTRAL", "reason": "<brief>"}},
    "BTCUSD":   {{"impact_pct": <float>, "direction": "UP"|"DOWN"|"NEUTRAL", "reason": "<brief>"}},
    "XAUUSD":   {{"impact_pct": <float>, "direction": "UP"|"DOWN"|"NEUTRAL", "reason": "<brief>"}}
  }},
  "sector_impacts": {{
    "Energy":   "<brief>",
    "Defense":  "<brief>",
    "Tech":     "<brief>",
    "Finance":  "<brief>"
  }},
  "risk_level": "LOW"|"MODERATE"|"HIGH"|"CRITICAL",
  "confidence": <float 0-1>,
  "timeframe": "short-term"|"medium-term"|"long-term"
}}"""

        try:
            resp = requests.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 800,
                },
                timeout=45,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            content = content.strip().strip("```json").strip("```").strip()
            return json.loads(content)
        except Exception as e:
            print(f"[WARN] AI simulation failed, using fallback: {e}")
            return None

    def _rule_based_simulate(self, event_type: str, magnitude: str, region: str) -> dict:
        """Generates a deterministic simulation result from impact templates."""
        key = (event_type.lower(), magnitude)
        impacts = IMPACT_TEMPLATES.get(
            key,
            IMPACT_TEMPLATES.get((event_type.lower(), "Moderate"), {"GOLD": +5, "OIL_BRENT": +3, "SP500": -5, "BTCUSD": -3})
        )

        affected_assets = {}
        for symbol, pct in impacts.items():
            direction = "UP" if pct > 0 else ("DOWN" if pct < 0 else "NEUTRAL")
            affected_assets[symbol] = {
                "impact_pct": abs(pct),
                "direction": direction,
                "reason": f"Historical pattern for {event_type} events in {region}.",
            }

        risk_map = {"Mild": "LOW", "Moderate": "MODERATE", "Severe": "HIGH", "Catastrophic": "CRITICAL"}
        risk_level = risk_map.get(magnitude, "MODERATE")

        return {
            "summary": (
                f"Based on historical patterns, a {magnitude.lower()} {event_type} event in {region} "
                f"is expected to trigger risk-off sentiment in equity markets while boosting safe-haven assets."
            ),
            "affected_assets": affected_assets,
            "sector_impacts": {
                "Energy": "Disruption likely due to regional instability.",
                "Defense": "Increased spending expected.",
                "Tech": "Supply chain concerns may pressure valuations.",
                "Finance": "Capital flight to safe-haven assets anticipated.",
            },
            "risk_level": risk_level,
            "confidence": 0.65,
            "timeframe": "short-term",
            "source": "rule-based-fallback",
        }


simulation_service = SimulationService()
