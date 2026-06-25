"""
Vol-Spike Ensemble Model
========================
Predicts whether a geopolitical event will trigger a 1-sigma volatility spike
in affected asset prices within 3-5 trading days.

Architecture:
  PRIMARY:   XGBoost binary classifier + LightGBM regressor ensemble
  CALIBRATOR: Ridge regression bias corrector (loaded from saved_models)
  FALLBACK:  Heuristic rule (severity × sector_sensitivity → score)

Models are loaded lazily from `backend/app/ml/saved_models/vol_spike_*.pkl`.
If models are not trained yet, the system gracefully falls back to the
deterministic heuristic — no crash, no degraded startup.

Output:
    {
        "vol_spike_prob":    float 0-1,   # P(|Δprice| > 1σ within 5 days)
        "vol_spike_signal":  "SPIKE" | "CALM",
        "vol_spike_mag":     float,       # predicted annualized vol increase
        "source":            "ensemble" | "heuristic"
    }
"""

import os
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger("geotrade.ml.vol_spike.vol_spike_model")

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "saved_models"
)

# Threshold above which we classify as SPIKE
VOL_SPIKE_THRESHOLD = 0.55


class VolSpikeModel:
    """
    Ensemble Vol-Spike classifier + regressor.

    On load:
      - Tries to load `vol_spike_classifier.pkl`  (XGBoost BinaryClassifier)
      - Tries to load `vol_spike_magnitude.pkl`   (LightGBM Regressor for mag)
      - Tries to load `vol_spike_calibrator.pkl`  (Ridge bias corrector)

    All loads are lazy and silent — the system always functions even without
    trained models.
    """

    _clf        = None
    _mag_reg    = None
    _calibrator = None
    _loaded     = False
    _failed     = False

    def _load_models(self):
        """Lazy-loads vol-spike models on first call."""
        if self._loaded or self._failed:
            return
        try:
            import joblib
            models_dir = os.path.abspath(MODELS_DIR)

            clf_path  = os.path.join(models_dir, "vol_spike_classifier.pkl")
            mag_path  = os.path.join(models_dir, "vol_spike_magnitude.pkl")
            cal_path  = os.path.join(models_dir, "vol_spike_calibrator.pkl")

            if os.path.exists(clf_path):
                VolSpikeModel._clf = joblib.load(clf_path)
                logger.info("Loaded vol_spike_classifier from %s", clf_path)

            if os.path.exists(mag_path):
                VolSpikeModel._mag_reg = joblib.load(mag_path)
                logger.info("Loaded vol_spike_magnitude regressor")

            if os.path.exists(cal_path):
                VolSpikeModel._calibrator = joblib.load(cal_path)
                logger.info("Loaded vol_spike Ridge calibrator")

            VolSpikeModel._loaded = True

        except Exception as exc:
            logger.warning(
                "Vol-spike model load failed: %s. Falling back to heuristic.", exc
            )
            VolSpikeModel._failed = True

    def predict(self, feature_vec: np.ndarray) -> dict:
        """
        Runs the vol-spike ensemble on a 15-dim feature vector.

        Args:
            feature_vec: (15,) float32 numpy array from VolSpikeFeatureBuilder

        Returns:
            {
                "vol_spike_prob":   float 0-1,
                "vol_spike_signal": "SPIKE" | "CALM",
                "vol_spike_mag":    float (predicted annualized vol increase),
                "source":           "ensemble" | "heuristic"
            }
        """
        self._load_models()

        if self._loaded and self._clf is not None:
            return self._ensemble_predict(feature_vec)

        return self._heuristic_predict(feature_vec)

    def _ensemble_predict(self, feature_vec: np.ndarray) -> dict:
        """Runs the trained XGBoost + LightGBM ensemble."""
        try:
            import pandas as pd
            X = feature_vec.reshape(1, -1)

            # Raw XGBoost probability
            raw_prob = float(self._clf.predict_proba(X)[0][1])

            # Ridge calibration (if available)
            if self._calibrator is not None:
                cal_input = np.array([[raw_prob]])
                prob = float(np.clip(self._calibrator.predict(cal_input)[0], 0.0, 1.0))
            else:
                prob = raw_prob

            # LightGBM magnitude prediction (if available)
            mag = 0.0
            if self._mag_reg is not None:
                mag = float(np.clip(self._mag_reg.predict(X)[0], 0.0, 1.0))

            return {
                "vol_spike_prob":   round(prob, 4),
                "vol_spike_signal": "SPIKE" if prob >= VOL_SPIKE_THRESHOLD else "CALM",
                "vol_spike_mag":    round(mag, 4),
                "source":           "ensemble",
            }
        except Exception as exc:
            logger.warning("Ensemble predict failed: %s. Using heuristic.", exc)
            return self._heuristic_predict(feature_vec)

    def _heuristic_predict(self, feature_vec: np.ndarray) -> dict:
        """
        Deterministic fallback based on feature vector structure.
        Feature indices (matching VolSpikeFeatureBuilder):
          1 = severity_norm
          9 = vix_norm
          13 = sector_sensitivity
          14 = asset_beta_to_event
        """
        severity_norm = float(feature_vec[1]) if len(feature_vec) > 1 else 0.5
        vix_norm      = float(feature_vec[9]) if len(feature_vec) > 9 else 0.2
        sens_abs      = abs(float(feature_vec[13])) if len(feature_vec) > 13 else 0.3
        beta          = float(feature_vec[14]) if len(feature_vec) > 14 else 0.3

        # Simple weighted heuristic
        prob = float(np.clip(
            0.35 * severity_norm +
            0.25 * vix_norm +
            0.20 * sens_abs +
            0.20 * beta,
            0.0, 1.0
        ))
        mag  = round(prob * 0.30, 4)   # rough annualized vol increase estimate

        return {
            "vol_spike_prob":   round(prob, 4),
            "vol_spike_signal": "SPIKE" if prob >= VOL_SPIKE_THRESHOLD else "CALM",
            "vol_spike_mag":    mag,
            "source":           "heuristic",
        }


# Singleton instance
vol_spike_model = VolSpikeModel()
