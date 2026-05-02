"""
Tests for SignalSchema Pydantic validation.
Verifies that invalid data is rejected with a ValidationError.
"""
import pytest
from pydantic import ValidationError

from app.schemas.signal_schema import SignalCreate, Signal


# ── Valid signal fixture ─────────────────────────────────────────────────────

VALID_SIGNAL = dict(
    market_id=1,
    signal_type="BUY",
    confidence=0.75,
    uncertainty=0.25,
    bullish_strength=0.75,
    bearish_strength=0.25,
    entry_price=100.0,
    stop_loss=95.0,
    target_price=110.0,
    risk_reward_ratio=2.0,
    signal_strength=0.6,
    volatility_level="Medium",
    reasoning="Test signal",
    risk_factors=["risk1"],
    tags=["ml-generated"],
)


class TestSignalCreateValidation:

    def test_valid_buy_signal(self):
        """A fully valid BUY signal should be accepted."""
        s = SignalCreate(**VALID_SIGNAL)
        assert s.signal_type == "BUY"
        assert s.confidence == 0.75

    def test_valid_sell_signal(self):
        """SELL is a valid signal type."""
        data = {**VALID_SIGNAL, "signal_type": "SELL"}
        s = SignalCreate(**data)
        assert s.signal_type == "SELL"

    def test_valid_hold_signal(self):
        """HOLD is a valid signal type."""
        data = {**VALID_SIGNAL, "signal_type": "HOLD"}
        s = SignalCreate(**data)
        assert s.signal_type == "HOLD"

    def test_invalid_signal_type_rejected(self):
        """An unknown signal type like 'LONG' should raise ValidationError."""
        data = {**VALID_SIGNAL, "signal_type": "LONG"}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_lowercase_signal_type_rejected(self):
        """Lowercase 'buy' should be rejected (schema is case-sensitive)."""
        data = {**VALID_SIGNAL, "signal_type": "buy"}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_confidence_above_1_rejected(self):
        """confidence > 1.0 should be rejected."""
        data = {**VALID_SIGNAL, "confidence": 1.5}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_confidence_below_0_rejected(self):
        """confidence < 0.0 should be rejected."""
        data = {**VALID_SIGNAL, "confidence": -0.1}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_uncertainty_above_1_rejected(self):
        """uncertainty > 1.0 should be rejected."""
        data = {**VALID_SIGNAL, "uncertainty": 1.1}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_signal_strength_above_1_rejected(self):
        """signal_strength > 1.0 should be rejected."""
        data = {**VALID_SIGNAL, "signal_strength": 2.0}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_negative_entry_price_rejected(self):
        """Negative entry_price should be rejected."""
        data = {**VALID_SIGNAL, "entry_price": -10.0}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_negative_stop_loss_rejected(self):
        """Negative stop_loss should be rejected."""
        data = {**VALID_SIGNAL, "stop_loss": -5.0}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_invalid_volatility_level_rejected(self):
        """volatility_level must be exactly 'Low', 'Medium', or 'High'."""
        data = {**VALID_SIGNAL, "volatility_level": "Very High"}
        with pytest.raises(ValidationError):
            SignalCreate(**data)

    def test_optional_fields_can_be_none(self):
        """All optional fields should accept None."""
        minimal = dict(market_id=1, signal_type="BUY", confidence=0.5)
        s = SignalCreate(**minimal)
        assert s.uncertainty is None
        assert s.stop_loss is None
        assert s.tags is None

    def test_boundary_confidence_zero(self):
        """confidence = 0.0 is valid (boundary)."""
        data = {**VALID_SIGNAL, "confidence": 0.0}
        s = SignalCreate(**data)
        assert s.confidence == 0.0

    def test_boundary_confidence_one(self):
        """confidence = 1.0 is valid (boundary)."""
        data = {**VALID_SIGNAL, "confidence": 1.0}
        s = SignalCreate(**data)
        assert s.confidence == 1.0

    def test_negative_risk_reward_rejected(self):
        """Negative risk_reward_ratio should be rejected."""
        data = {**VALID_SIGNAL, "risk_reward_ratio": -1.0}
        with pytest.raises(ValidationError):
            SignalCreate(**data)
