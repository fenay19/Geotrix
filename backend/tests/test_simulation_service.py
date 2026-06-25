"""
Unit tests for SimulationService business logic.
External AI calls are mocked; only the deterministic code paths are tested here.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.simulation_service import SimulationService, IMPACT_TEMPLATES


service = SimulationService()


# ── _rule_based_simulate ──────────────────────────────────────────────────────

class TestRuleBasedSimulate:

    def test_war_severe_uses_template(self):
        """War / Severe should apply the correct IMPACT_TEMPLATE."""
        result = service._rule_based_simulate("war", "Severe", "Middle East")
        assets = result["affected_assets"]
        # Gold should go UP in a war scenario
        assert assets["GOLD"]["direction"] == "UP"
        assert assets["GOLD"]["impact_pct"] > 0
        # S&P 500 should go DOWN
        assert assets["SP500"]["direction"] == "DOWN"

    def test_unknown_event_type_falls_back_to_moderate(self):
        """An unknown event type should fall back gracefully to a default template."""
        result = service._rule_based_simulate("volcano", "Severe", "Iceland")
        assert "summary" in result
        assert "affected_assets" in result
        # Should still have the four core assets
        for asset in ["GOLD", "OIL_BRENT", "SP500", "BTCUSD"]:
            assert asset in result["affected_assets"]

    def test_risk_level_mapping_severe(self):
        """Severe magnitude should map to HIGH risk_level."""
        result = service._rule_based_simulate("war", "Severe", "Eastern Europe")
        assert result["risk_level"] == "HIGH"

    def test_risk_level_mapping_mild(self):
        """Mild magnitude should map to LOW risk_level."""
        result = service._rule_based_simulate("policy", "Mild", "Asia")
        assert result["risk_level"] == "LOW"

    def test_risk_level_mapping_catastrophic(self):
        """Catastrophic magnitude should map to CRITICAL risk_level."""
        result = service._rule_based_simulate("war", "Catastrophic", "Global")
        assert result["risk_level"] == "CRITICAL"

    def test_confidence_is_reasonable(self):
        """Rule-based confidence should be fixed at 0.65."""
        result = service._rule_based_simulate("economic", "Severe", "EU")
        assert result["confidence"] == 0.65

    def test_source_is_rule_based_fallback(self):
        """Source field should clearly indicate rule-based origin."""
        result = service._rule_based_simulate("sanctions", "Severe", "Russia")
        assert result["source"] == "rule-based-fallback"

    def test_all_assets_have_required_keys(self):
        """Each asset entry must have impact_pct, direction, and reason."""
        result = service._rule_based_simulate("war", "Moderate", "Asia")
        for symbol, data in result["affected_assets"].items():
            assert "impact_pct" in data, f"impact_pct missing for {symbol}"
            assert "direction" in data, f"direction missing for {symbol}"
            assert "reason" in data, f"reason missing for {symbol}"

    def test_impact_pct_is_positive(self):
        """impact_pct should always be stored as a positive value (direction carries sign)."""
        result = service._rule_based_simulate("war", "Severe", "Middle East")
        for symbol, data in result["affected_assets"].items():
            assert data["impact_pct"] >= 0, f"Negative impact_pct for {symbol}"

    def test_summary_contains_event_type(self):
        """Summary should reference the event type for context."""
        result = service._rule_based_simulate("economic", "Severe", "Asia")
        assert "economic" in result["summary"].lower()

    def test_sector_impacts_present(self):
        """sector_impacts must include Energy, Defense, Tech, Finance."""
        result = service._rule_based_simulate("war", "Severe", "Middle East")
        for sector in ["Energy", "Defense", "Tech", "Finance"]:
            assert sector in result["sector_impacts"]


# ── run_scenario (with AI mocked) ─────────────────────────────────────────────

class TestRunScenario:
    def test_falls_back_to_rule_based_when_ai_unavailable(self):
        """When OpenAI key is absent, the service should use the rule-based fallback."""
        db = MagicMock()

        # Mock GTI
        gti = MagicMock()
        gti.current_score = 60.0

        # Mock repositories
        with patch("app.services.simulation_service.GTIRepository") as MockGTI, \
             patch("app.services.simulation_service.EventRepository") as MockEvent, \
             patch("app.services.simulation_service.SimulationRepository") as MockSimRepo, \
             patch("app.services.simulation_service.settings") as MockSettings:
            
            MockGTI.return_value.get_latest.return_value = gti
            MockEvent.return_value.get_high_severity.return_value = []
            MockSettings.OPENAI_API_KEY = None  # No AI key → force fallback

            saved_sim = MagicMock()
            saved_sim.id = 42
            MockSimRepo.return_value.create.return_value = saved_sim

            result = service.run_scenario(
                db=db,
                scenario_name="Test Conflict",
                region="Middle East",
                event_type="war",
                magnitude="Severe",
            )

        assert result is not None
        assert result.id == 42
        # Verify the simulation was saved
        MockSimRepo.return_value.create.assert_called_once()
