"""
Kelly Criterion Position Sizer
================================
Computes the optimal fraction of capital to allocate to a trade using
the Kelly Criterion, adjusted for volatility regime and signal confidence.

Kelly Formula (continuous):
    f* = (p - q) / b
  where:
    p  = probability of winning (signal confidence)
    q  = 1 - p (probability of losing)
    b  = win/loss ratio (approximated from risk-reward ratio)

Adjustments applied:
  1. HALF-KELLY: f* is halved to reduce variance (standard in practice)
  2. VOL-SCALING: reduce position in high-volatility regimes
  3. IMPACT-SCALING: scale by |impact_score| from propagator
  4. HARD CAP: maximum 25% of capital in any single position

Reference: Thorp, E.O. (1962). Beat the Dealer. Kelly (1956). A New
           Interpretation of Information Rate.
"""

import logging
import math

logger = logging.getLogger("geotrade.ml.impact_graph.kelly_sizer")

# ── Constants ──────────────────────────────────────────────────────────────────
MAX_KELLY_FRACTION = 0.25   # Hard cap: never risk more than 25% per trade
MIN_KELLY_FRACTION = 0.01   # Minimum to produce a non-trivial signal
HALF_KELLY         = 0.5    # Standard half-Kelly multiplier
VOL_HIGH_THRESHOLD = 0.30   # Annualized vol above this = "high-vol regime"
VOL_HIGH_PENALTY   = 0.5    # Reduce Kelly fraction by 50% in high-vol regime


def compute_kelly_fraction(
    confidence:           float,
    risk_reward_ratio:    float,
    impact_score:         float  = 1.0,
    vol_20d:              float  = 0.15,
    apply_half_kelly:     bool   = True,
    max_fraction:         float  = MAX_KELLY_FRACTION,
) -> float:
    """
    Computes the Kelly-optimal position fraction (capped at max_fraction).

    Args:
        confidence:        Signal confidence 0-1 (model win probability)
        risk_reward_ratio: abs(target - entry) / abs(entry - stop_loss)
        impact_score:      |impact| from ImpactNode (0-1), scales position
        vol_20d:           Annualized 20-day realized volatility
        apply_half_kelly:  Whether to apply the half-Kelly reduction
        max_fraction:      Maximum allowed fraction (default 0.25)

    Returns:
        kelly_fraction: float in [0, max_fraction]
    """
    p = float(min(max(confidence, 0.01), 0.99))
    q = 1.0 - p
    b = float(max(risk_reward_ratio, 0.1))  # protect against zero/negative RR

    # Standard Kelly formula
    kelly_raw = (p * b - q) / b

    if kelly_raw <= 0:
        logger.debug(
            "Kelly fraction is non-positive (%.4f): confidence=%.2f, RR=%.2f. "
            "Returning 0 — do not trade.",
            kelly_raw, p, b
        )
        return 0.0

    # Half-Kelly reduction (standard de-risking)
    fraction = kelly_raw * (HALF_KELLY if apply_half_kelly else 1.0)

    # Volatility regime adjustment
    if vol_20d > VOL_HIGH_THRESHOLD:
        vol_scale = VOL_HIGH_PENALTY
        logger.debug(
            "High-vol regime (vol_20d=%.2f > %.2f): applying %.0f%% vol penalty",
            vol_20d, VOL_HIGH_THRESHOLD, vol_scale * 100
        )
        fraction *= vol_scale

    # Impact scaling: proportional to event magnitude
    impact_abs = float(min(abs(impact_score), 1.0))
    if impact_abs < 0.10:
        impact_abs = 0.50  # use 50% as neutral default if no impact info
    fraction *= impact_abs

    # Apply hard cap
    fraction = float(min(fraction, max_fraction))
    fraction = float(max(fraction, 0.0))

    logger.debug(
        "Kelly sizing: confidence=%.2f, RR=%.2f, vol=%.2f, impact=%.2f -> fraction=%.4f",
        p, b, vol_20d, impact_abs, fraction
    )
    return round(fraction, 4)


def compute_position_size(
    capital:              float,
    entry_price:          float,
    confidence:           float,
    risk_reward_ratio:    float,
    impact_score:         float  = 1.0,
    vol_20d:              float  = 0.15,
    max_fraction:         float  = MAX_KELLY_FRACTION,
) -> dict:
    """
    Computes position size in units and dollar amount.

    Args:
        capital:           Total portfolio capital in USD
        entry_price:       Asset entry price
        confidence:        Signal confidence 0-1
        risk_reward_ratio: Risk-reward ratio from signal
        impact_score:      Propagator impact magnitude
        vol_20d:           Annualized realized volatility
        max_fraction:      Hard cap on position fraction

    Returns:
        {
            "kelly_fraction":    float,   # fraction of capital to deploy
            "position_usd":      float,   # dollar amount to invest
            "shares":            float,   # shares / units to buy
            "max_loss_usd":      float,   # capital at risk
        }
    """
    fraction   = compute_kelly_fraction(
        confidence        = confidence,
        risk_reward_ratio = risk_reward_ratio,
        impact_score      = impact_score,
        vol_20d           = vol_20d,
        max_fraction      = max_fraction,
    )

    position_usd = round(capital * fraction, 2)
    shares       = round(position_usd / max(entry_price, 0.01), 6)

    # Max loss estimate: position × (1 - stop_loss_ratio)
    # Using 2 × daily_sigma as proxy for stop distance
    daily_sigma   = vol_20d / math.sqrt(252)
    stop_distance = 2.0 * daily_sigma
    max_loss_usd  = round(position_usd * stop_distance, 2)

    return {
        "kelly_fraction":  fraction,
        "position_usd":    position_usd,
        "shares":          shares,
        "max_loss_usd":    max_loss_usd,
    }


# Convenience functions for signal_service integration
def kelly_fraction_from_signal(signal_data: dict, vol_20d: float = 0.15) -> float:
    """
    Extracts Kelly fraction from a signal dict (as produced by signal_service).
    Compatible with the existing SignalCreate schema.
    """
    return compute_kelly_fraction(
        confidence        = float(signal_data.get("confidence", 0.6)),
        risk_reward_ratio = float(signal_data.get("risk_reward_ratio", 1.5)),
        impact_score      = float(signal_data.get("impact_score", 0.5)),
        vol_20d           = vol_20d,
    )
