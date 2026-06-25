"""
Vol-Spike Feature Builder
==========================
Converts a geopolitical event + market context into a 15-dimensional
feature vector for the Vol-Spike ensemble classifier/regressor.

Feature groups:
  [0-4]   Event-derived features (event_type_id, severity, escalation, sentiment, confidence)
  [5-8]   Country-risk features  (country_risk, gti_score, casualties_norm, econ_damage_norm)
  [9-12]  Market-regime features (vix, vol_20d, garch_sigma, dist_52w_high)
  [13-14] Asset-class sensitivity (sector_sensitivity, asset_beta_to_event)
"""

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger("geotrade.ml.vol_spike.feature_builder")

# ── Event-type integer encoding ───────────────────────────────────────────────
EVENT_TYPE_IDS = {
    "war":          0,
    "conflict":     1,
    "sanctions":    2,
    "unrest":       3,
    "economic":     4,
    "policy":       5,
}

# ── Asset-class → event-type sensitivity matrix ───────────────────────────────
# Rows = asset categories (matching ml_predictor.SYMBOL_TO_ASSET values)
# Cols = event_type_id (war, conflict, sanctions, unrest, economic, policy)
# Values = signed sensitivity coefficient [-1.0 to +1.0]
#   Positive  = asset price RISES on this event type (risk-haven / defense)
#   Negative  = asset price FALLS on this event type (risk-off penalty)
#   Near-zero = asset largely insensitive to this event type
SECTOR_SENSITIVITY = {
    # Asset cat       war   conflict  sanctions  unrest  economic  policy
    "GOLD":         [ 0.85,  0.70,    0.60,      0.50,   0.30,    -0.10],
    "OIL_BRENT":    [ 0.75,  0.65,    0.55,      0.40,   0.20,    -0.05],
    "SP500":        [-0.80, -0.65,   -0.55,     -0.45,  -0.70,    -0.20],
    "TECH":         [-0.70, -0.50,   -0.65,     -0.30,  -0.60,    -0.15],
    "BTCUSD":       [-0.55, -0.40,   -0.40,     -0.60,  -0.50,    -0.10],
    "BONDS":        [ 0.60,  0.50,    0.40,      0.30,   0.55,     0.10],
    "DOLLAR":       [ 0.40,  0.30,    0.35,      0.25,   0.30,     0.05],
    "EM_EQUITY":    [-0.75, -0.60,   -0.80,     -0.55,  -0.65,    -0.25],
    "INDIA_EQUITY": [-0.45, -0.55,   -0.40,     -0.35,  -0.50,    -0.15],
    "CHINA_EQUITY": [-0.60, -0.50,   -0.90,     -0.40,  -0.65,    -0.20],
    "EUROPE_EQUITY":[-0.70, -0.65,   -0.60,     -0.50,  -0.60,    -0.20],
    "JAPAN_EQUITY": [-0.50, -0.45,   -0.35,     -0.30,  -0.55,    -0.10],
    "BRAZIL_EQUITY":[-0.55, -0.50,   -0.60,     -0.55,  -0.65,    -0.20],
    "GOLD_ETF":     [ 0.80,  0.68,    0.58,      0.48,   0.28,    -0.10],
}

# Default sensitivity for unknown asset categories
_DEFAULT_SENSITIVITY = [-0.30, -0.25, -0.25, -0.20, -0.30, -0.10]


def get_sector_sensitivity(asset_category: str, event_type: str) -> float:
    """
    Returns the scalar sensitivity of an asset category to a given event type.
    Positive = price typically rises, negative = price typically falls.
    """
    row = SECTOR_SENSITIVITY.get(asset_category, _DEFAULT_SENSITIVITY)
    col = EVENT_TYPE_IDS.get(event_type, 5)  # default to "policy" (col 5)
    return float(row[col])


class VolSpikeFeatureBuilder:
    """
    Builds the 15-feature vector from a geopolitical event + market context.

    Feature vector layout (indices):
      0:  event_type_id        (int 0-5)
      1:  severity             (float 1-10, normalized to 0-1)
      2:  escalation_potential (float 1-5, normalized to 0-1)
      3:  sentiment_signed     (float -1 to +1)
      4:  nlp_confidence       (float 0-1)
      5:  country_risk_score   (float 0-100, normalized to 0-1)
      6:  gti_score            (float 0-100, normalized to 0-1)
      7:  casualties_norm      (log1p(casualties) / 10, clipped 0-1)
      8:  econ_damage_norm     (log1p(damage_usd) / 15, clipped 0-1)
      9:  vix                  (float, normalized vix/80)
      10: vol_20d              (float annualized, clipped at 1.0)
      11: garch_sigma_1d       (float daily vol)
      12: dist_52w_high        (float ≤ 0, how far from 52-week high)
      13: sector_sensitivity   (float -1 to +1)
      14: asset_beta_to_event  (abs(sector_sensitivity) * severity_norm)
    """

    N_FEATURES = 15

    def build(
        self,
        event_type: str,
        severity: float,
        escalation_potential: float,
        sentiment_signed: float,
        nlp_confidence: float,
        country_risk_score: float,
        gti_score: float,
        casualties: float,
        econ_damage_million_usd: float,
        vix: float,
        vol_20d: float,
        garch_sigma_1d: float,
        dist_52w_high: float,
        asset_category: str,
    ) -> np.ndarray:
        """
        Returns a (15,) float32 numpy array.
        All values are clipped and normalized to reduce sensitivity to outliers.
        """
        severity_norm = float(np.clip(severity / 10.0, 0.0, 1.0))
        esc_norm      = float(np.clip(escalation_potential / 5.0, 0.0, 1.0))
        sent          = float(np.clip(sentiment_signed, -1.0, 1.0))
        conf          = float(np.clip(nlp_confidence, 0.0, 1.0))
        cr_norm       = float(np.clip(country_risk_score / 100.0, 0.0, 1.0))
        gti_norm      = float(np.clip(gti_score / 100.0, 0.0, 1.0))
        cas_norm      = float(np.clip(np.log1p(max(0.0, casualties)) / 10.0, 0.0, 1.0))
        dmg_norm      = float(np.clip(np.log1p(max(0.0, econ_damage_million_usd)) / 15.0, 0.0, 1.0))
        vix_norm      = float(np.clip(vix / 80.0, 0.0, 1.0))
        vol_norm      = float(np.clip(vol_20d, 0.0, 1.0))
        garch_norm    = float(np.clip(garch_sigma_1d, 0.0, 0.10))
        d52w          = float(np.clip(dist_52w_high, -1.0, 0.0))
        sens          = get_sector_sensitivity(asset_category, event_type)
        beta          = abs(sens) * severity_norm

        vec = np.array([
            float(EVENT_TYPE_IDS.get(event_type, 5)),
            severity_norm,
            esc_norm,
            sent,
            conf,
            cr_norm,
            gti_norm,
            cas_norm,
            dmg_norm,
            vix_norm,
            vol_norm,
            garch_norm,
            d52w,
            sens,
            beta,
        ], dtype=np.float32)

        return vec

    def build_from_event_dict(
        self,
        analysis: dict,
        market_features: dict,
        asset_category: str,
    ) -> np.ndarray:
        """
        Convenience wrapper: builds a feature vector from the dicts already
        produced by the pipeline (analysis from AI eval + market features from predictor).
        """
        return self.build(
            event_type               = analysis.get("event_type", "policy"),
            severity                 = float(analysis.get("severity", 5)),
            escalation_potential     = float(analysis.get("escalation_potential", 2)),
            sentiment_signed         = float(analysis.get("sentiment_signed", 0.0)),
            nlp_confidence           = float(analysis.get("nlp_confidence", 0.5)),
            country_risk_score       = float(market_features.get("country_risk_score", 50.0)),
            gti_score                = float(market_features.get("gti_score", 50.0)),
            casualties               = float(analysis.get("casualties", 0)),
            econ_damage_million_usd  = float(analysis.get("economic_damage_million_usd", 0.0)),
            vix                      = float(market_features.get("vix", 15.0)),
            vol_20d                  = float(market_features.get("vol_20d", 0.15)),
            garch_sigma_1d           = float(market_features.get("garch_sigma_1d", 0.01)),
            dist_52w_high            = float(market_features.get("dist_52w_high", 0.0)),
            asset_category           = asset_category,
        )


# Singleton instance
vol_spike_feature_builder = VolSpikeFeatureBuilder()
