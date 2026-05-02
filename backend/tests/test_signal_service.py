"""
Unit tests for the SignalService business logic.
Tests are fully isolated: no DB, no external APIs.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.services.signal_service import SignalService
from app.schemas.signal_schema import SignalCreate


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_market(symbol="SPY", price=450.0, category="Index", country_id=None):
    m = MagicMock()
    m.id = 1
    m.symbol = symbol
    m.price = price
    m.category = category
    m.country_id = country_id
    return m


def _make_country_risk(risk_score=60.0):
    cr = MagicMock()
    cr.risk_score = risk_score
    cr.country_name = "TestLand"
    return cr


service = SignalService()


# ── calculate_signal_strength ─────────────────────────────────────────────────

class TestCalculateSignalStrength:
    def test_high_confidence_low_vol(self):
        """High confidence + low volatility should yield a high strength."""
        strength = service.calculate_signal_strength(
            confidence=0.95, garch_sigma=0.01, vix=12.0, threshold=0.45
        )
        assert 0.7 <= strength <= 1.0

    def test_barely_above_threshold(self):
        """Confidence just above threshold should give a small positive strength."""
        strength = service.calculate_signal_strength(
            confidence=0.50, garch_sigma=0.02, vix=20.0, threshold=0.45
        )
        assert 0.0 < strength < 0.3

    def test_below_threshold_is_zero(self):
        """Confidence below threshold should clamp to 0.0."""
        strength = service.calculate_signal_strength(
            confidence=0.40, garch_sigma=0.02, vix=20.0, threshold=0.45
        )
        assert strength == 0.0

    def test_high_volatility_penalizes_strength(self):
        """High GARCH sigma (extreme volatility) should significantly reduce strength."""
        low_vol = service.calculate_signal_strength(0.9, garch_sigma=0.01, vix=12.0, threshold=0.45)
        high_vol = service.calculate_signal_strength(0.9, garch_sigma=0.20, vix=12.0, threshold=0.45)
        assert low_vol > high_vol

    def test_returns_float_in_range(self):
        """Return value must always be in [0.0, 1.0]."""
        for conf in [0.0, 0.45, 0.7, 1.0]:
            s = service.calculate_signal_strength(conf, garch_sigma=0.05, vix=15.0, threshold=0.45)
            assert 0.0 <= s <= 1.0, f"Strength out of range for confidence={conf}: {s}"


# ── get_raf ───────────────────────────────────────────────────────────────────

class TestGetRAF:
    def test_returns_default_on_exception(self):
        """If yfinance throws, RAF should default to 1.0."""
        with patch("app.services.signal_service.yf.Ticker", side_effect=RuntimeError("network error")):
            raf = service.get_raf("SPY")
        assert raf == 1.0

    def test_returns_default_for_no_fundamentals(self):
        """Commodities/crypto with no balance sheet metrics should return 1.0."""
        mock_ticker = MagicMock()
        mock_ticker.info = {"regularMarketPrice": 100}  # no ROE/D-E/ROA keys
        with patch("app.services.signal_service.yf.Ticker", return_value=mock_ticker):
            raf = service.get_raf("GC=F")
        assert raf == 1.0

    def test_clamps_to_min(self):
        """RAF must be >= 0.5 even when fundamentals are very positive."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "returnOnEquity": 5.0,   # extreme ROE
            "debtToEquity": 0.0,
            "returnOnAssets": 3.0,
        }
        with patch("app.services.signal_service.yf.Ticker", return_value=mock_ticker):
            raf = service.get_raf("AAPL")
        assert raf >= 0.5

    def test_clamps_to_max(self):
        """RAF must be <= 1.5 even when fundamentals are very negative."""
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "returnOnEquity": -5.0,
            "debtToEquity": 10000.0,
            "returnOnAssets": -3.0,
        }
        with patch("app.services.signal_service.yf.Ticker", return_value=mock_ticker):
            raf = service.get_raf("JUNK")
        assert raf <= 1.5

    def test_ticker_map_used_for_btc(self):
        """BTC-USD should be requested, not BTCUSD."""
        mock_ticker = MagicMock()
        mock_ticker.info = {}
        with patch("app.services.signal_service.yf.Ticker", return_value=mock_ticker) as mock_yf:
            service.get_raf("BTCUSD")
        mock_yf.assert_called_once_with("BTC-USD")


# ── _rule_based_signal ────────────────────────────────────────────────────────

class TestRuleBasedSignal:
    def test_high_risk_generates_sell(self):
        """Combined score > 65 should produce a SELL signal."""
        market = _make_market(price=100.0)
        country_risk = _make_country_risk(risk_score=80.0)
        # combined = gti(80)*0.6 + cr(80)*0.4 = 80 > 65
        result = service._rule_based_signal(market, gti_score=80.0, country_risk=country_risk)
        assert result.signal_type == "SELL"
        assert result.target_price < 100.0
        assert result.stop_loss > 100.0

    def test_low_risk_generates_buy(self):
        """Combined score < 38 should produce a BUY signal."""
        market = _make_market(price=100.0)
        country_risk = _make_country_risk(risk_score=10.0)
        # combined = gti(20)*0.6 + cr(10)*0.4 = 16 < 38
        result = service._rule_based_signal(market, gti_score=20.0, country_risk=country_risk)
        assert result.signal_type == "BUY"
        assert result.target_price > 100.0
        assert result.stop_loss < 100.0

    def test_moderate_risk_generates_hold(self):
        """Combined score 38–65 should produce a HOLD signal."""
        market = _make_market(price=100.0)
        country_risk = _make_country_risk(risk_score=50.0)
        # combined = 50*0.6 + 50*0.4 = 50 → HOLD
        result = service._rule_based_signal(market, gti_score=50.0, country_risk=country_risk)
        assert result.signal_type == "HOLD"

    def test_none_country_risk_defaults_to_50(self):
        """When country_risk is None, combined score should use 50 as default."""
        market = _make_market(price=200.0)
        # gti=50, cr=50 → combined=50 → HOLD
        result = service._rule_based_signal(market, gti_score=50.0, country_risk=None)
        assert result.signal_type == "HOLD"
        assert result.market_id == 1

    def test_signal_strength_is_set(self):
        """Rule-based signal must always include a non-None signal_strength."""
        market = _make_market(price=100.0)
        result = service._rule_based_signal(market, gti_score=80.0, country_risk=None)
        assert result.signal_strength is not None
        assert 0.0 <= result.signal_strength <= 1.0

    def test_confidence_in_valid_range(self):
        """Confidence should always be within [0.0, 1.0]."""
        for gti in [0, 20, 50, 80, 100]:
            market = _make_market(price=100.0)
            result = service._rule_based_signal(market, gti_score=float(gti), country_risk=None)
            assert 0.0 <= result.confidence <= 1.0, f"Confidence out of range at gti={gti}"

    def test_uncertainty_equals_one_minus_confidence(self):
        """uncertainty field should equal 1 - confidence (rounded)."""
        market = _make_market(price=100.0)
        result = service._rule_based_signal(market, gti_score=80.0, country_risk=None)
        expected = round(1 - result.confidence, 2)
        assert result.uncertainty == expected

    def test_zero_price_uses_default(self):
        """If market.price is 0 or None, it should default to 100.0 without errors."""
        market = _make_market(price=None)
        result = service._rule_based_signal(market, gti_score=80.0, country_risk=None)
        assert result.entry_price == 100.0

    def test_risk_reward_positive(self):
        """Risk-reward ratio must always be positive."""
        for gti in [20.0, 80.0]:
            market = _make_market(price=500.0)
            result = service._rule_based_signal(market, gti_score=gti, country_risk=None)
            assert result.risk_reward_ratio > 0

    def test_tags_include_rule_based(self):
        """Tags should always include 'rule-based-fallback'."""
        market = _make_market(price=100.0)
        result = service._rule_based_signal(market, gti_score=50.0, country_risk=None)
        assert "rule-based-fallback" in result.tags
