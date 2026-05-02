"""
Unit tests for RiskService business logic.
All DB interaction is mocked.
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from app.services.risk_service import RiskService


service = RiskService()


# ── _classify_color ───────────────────────────────────────────────────────────

class TestClassifyColor:
    def test_score_below_35_is_green(self):
        assert service._classify_color(0.0) == "Green"
        assert service._classify_color(34.9) == "Green"

    def test_score_35_to_64_is_yellow(self):
        assert service._classify_color(35.0) == "Yellow"
        assert service._classify_color(50.0) == "Yellow"
        assert service._classify_color(64.9) == "Yellow"

    def test_score_65_and_above_is_red(self):
        assert service._classify_color(65.0) == "Red"
        assert service._classify_color(90.0) == "Red"
        assert service._classify_color(100.0) == "Red"

    def test_exact_boundary_35(self):
        """35.0 is the first Yellow value."""
        assert service._classify_color(35.0) == "Yellow"

    def test_exact_boundary_65(self):
        """65.0 is the first Red value."""
        assert service._classify_color(65.0) == "Red"


# ── recalculate_country_risk ──────────────────────────────────────────────────

class TestRecalculateCountryRisk:

    def _make_db_with_country(self, risk_score=50.0, events=None):
        """Build a mock DB session that returns a country + event list."""
        country = MagicMock()
        country.id = 1
        country.country_code = "US"
        country.risk_score = risk_score
        country.color_code = "Yellow"

        repo_instance = MagicMock()
        repo_instance.get_by_code.return_value = country

        db = MagicMock()
        # Mock the event query chain
        query_mock = MagicMock()
        db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.all.return_value = events or []

        return db, country

    def test_returns_none_for_unknown_country(self):
        """If country not found, should return None gracefully."""
        with patch("app.services.risk_service.CountryRiskRepository") as MockRepo:
            MockRepo.return_value.get_by_code.return_value = None
            db = MagicMock()
            result = service.recalculate_country_risk(db, "XX")
        assert result is None

    def test_no_events_decreases_score(self):
        """With no recent events, risk score should decay by 10% (floored at 25)."""
        with patch("app.services.risk_service.CountryRiskRepository") as MockRepo:
            country = MagicMock()
            country.id = 1
            country.risk_score = 60.0
            country.color_code = "Yellow"
            MockRepo.return_value.get_by_code.return_value = country

            db = MagicMock()
            query_mock = MagicMock()
            db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.all.return_value = []

            result = service.recalculate_country_risk(db, "US")

        assert result.risk_score == 54.0  # 60 * 0.90

    def test_no_events_does_not_go_below_25(self):
        """Risk score should floor at 25 when no events and current score is already low."""
        with patch("app.services.risk_service.CountryRiskRepository") as MockRepo:
            country = MagicMock()
            country.id = 1
            country.risk_score = 26.0
            country.color_code = "Green"
            MockRepo.return_value.get_by_code.return_value = country

            db = MagicMock()
            query_mock = MagicMock()
            db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.all.return_value = []

            result = service.recalculate_country_risk(db, "US")

        assert result.risk_score == 25.0  # floored

    def test_color_updated_correctly(self):
        """Color code should be updated based on the new score."""
        with patch("app.services.risk_service.CountryRiskRepository") as MockRepo:
            country = MagicMock()
            country.id = 1
            country.risk_score = 30.0
            country.color_code = "Green"
            MockRepo.return_value.get_by_code.return_value = country

            db = MagicMock()
            query_mock = MagicMock()
            db.query.return_value = query_mock
            query_mock.filter.return_value = query_mock
            query_mock.all.return_value = []

            result = service.recalculate_country_risk(db, "US")

        # 30.0 - 5.0 = 25.0 → "Green"
        assert result.color_code == "Green"


# ── get_globe_data ─────────────────────────────────────────────────────────────

class TestGetGlobeData:
    def test_returns_list_of_dicts(self):
        """get_globe_data should return a list of formatted dicts."""
        with patch("app.services.risk_service.CountryRiskRepository") as MockRepo:
            c1 = MagicMock()
            c1.country_code = "US"
            c1.country_name = "United States"
            c1.risk_score = 45.0
            c1.color_code = "Yellow"
            c1.sector_exposure = {"Energy": 0.3}
            MockRepo.return_value.get_all.return_value = [c1]

            db = MagicMock()
            result = service.get_globe_data(db)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["country_code"] == "US"
        assert result[0]["risk_score"] == 45.0
        assert result[0]["sector_exposure"] == {"Energy": 0.3}

    def test_none_sector_exposure_defaults_to_empty_dict(self):
        """If sector_exposure is None on the model, it should appear as {}."""
        with patch("app.services.risk_service.CountryRiskRepository") as MockRepo:
            c1 = MagicMock()
            c1.country_code = "IN"
            c1.country_name = "India"
            c1.risk_score = 55.0
            c1.color_code = "Yellow"
            c1.sector_exposure = None  # simulate missing data
            MockRepo.return_value.get_all.return_value = [c1]

            db = MagicMock()
            result = service.get_globe_data(db)

        assert result[0]["sector_exposure"] == {}

    def test_empty_countries_returns_empty_list(self):
        """When no countries exist, should return an empty list."""
        with patch("app.services.risk_service.CountryRiskRepository") as MockRepo:
            MockRepo.return_value.get_all.return_value = []
            db = MagicMock()
            result = service.get_globe_data(db)
        assert result == []
