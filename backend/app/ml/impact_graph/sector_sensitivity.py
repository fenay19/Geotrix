"""
Sector-Sensitivity Matrix
==========================
Static predefined coefficients defining how each asset category responds
to each geopolitical event type.

Design decision (approved): Static coefficients scaled by NLP-extracted severity.
The coefficient encodes market consensus about typical asset price direction
on each event type. Severity from NLP scales the magnitude.

All values are in [-1.0, +1.0]:
  +1.0 = strongest positive price response (e.g. Gold on War)
  -1.0 = strongest negative price response (e.g. EM Equity on Sanctions)
   0.0 = neutral / uncorrelated

Reference: Goldman Sachs Geopolitical Risk Report (2022-2024),
           JPMorgan Cross-Asset Strategy, BIS Working Paper 912.
"""

from typing import Dict, List

# Event type ordering (must match vol_spike/feature_builder.py EVENT_TYPE_IDS)
EVENT_TYPES = ["war", "conflict", "sanctions", "unrest", "economic", "policy"]

# Asset-category × event-type matrix
# Row = asset_category | Col order = war, conflict, sanctions, unrest, economic, policy
SENSITIVITY_MATRIX: Dict[str, List[float]] = {
    # Safe Havens
    "GOLD":             [ 0.85,  0.70,  0.60,  0.50,  0.30, -0.10],
    "GOLD_ETF":         [ 0.82,  0.68,  0.58,  0.48,  0.28, -0.10],
    "BONDS":            [ 0.60,  0.50,  0.40,  0.30,  0.55,  0.10],
    "DOLLAR":           [ 0.40,  0.30,  0.35,  0.25,  0.30,  0.05],

    # Energy
    "OIL_BRENT":        [ 0.75,  0.65,  0.55,  0.40,  0.20, -0.05],

    # Equity — Developed
    "SP500":            [-0.80, -0.65, -0.55, -0.45, -0.70, -0.20],
    "EUROPE_EQUITY":    [-0.75, -0.70, -0.60, -0.52, -0.62, -0.22],
    "JAPAN_EQUITY":     [-0.55, -0.48, -0.38, -0.32, -0.58, -0.12],

    # Equity — Tech
    "TECH":             [-0.70, -0.52, -0.65, -0.32, -0.62, -0.16],

    # Equity — Emerging
    "EM_EQUITY":        [-0.78, -0.62, -0.82, -0.57, -0.67, -0.27],
    "INDIA_EQUITY":     [-0.50, -0.58, -0.42, -0.37, -0.52, -0.18],
    "CHINA_EQUITY":     [-0.62, -0.52, -0.92, -0.42, -0.67, -0.22],
    "BRAZIL_EQUITY":    [-0.58, -0.52, -0.62, -0.58, -0.68, -0.22],

    # Crypto
    "BTCUSD":           [-0.58, -0.42, -0.42, -0.62, -0.52, -0.12],
}

# Default row for unknown asset categories
_DEFAULT_ROW: List[float] = [-0.30, -0.25, -0.25, -0.20, -0.30, -0.10]

# Event-type index lookup
_EVENT_IDX: Dict[str, int] = {e: i for i, e in enumerate(EVENT_TYPES)}


def get_sensitivity(asset_category: str, event_type: str) -> float:
    """
    Returns scalar sensitivity of asset_category to event_type.
    Scaled by severity externally:  impact = severity_norm × get_sensitivity(...)
    """
    row = SENSITIVITY_MATRIX.get(asset_category, _DEFAULT_ROW)
    idx = _EVENT_IDX.get(event_type, len(EVENT_TYPES) - 1)  # default = "policy"
    return float(row[idx])


def get_all_sensitivities(event_type: str) -> Dict[str, float]:
    """
    Returns sensitivity for ALL tracked asset categories for a given event type.
    Useful for the impact propagator to fan out an event across all assets.
    """
    return {
        cat: get_sensitivity(cat, event_type)
        for cat in SENSITIVITY_MATRIX
    }
