"""
Ridge Bias Calibrator
=====================
Trains and saves a Ridge regression calibrator that corrects systematic
over/under-confidence in the raw Vol-Spike XGBoost probabilities.

Usage (offline training — run once after training vol_spike_classifier.pkl):
    python -m app.ml.vol_spike.ridge_calibrator

This script:
  1. Loads the already-trained vol_spike_classifier.pkl
  2. Fetches 1y of historical geopolitical events + VIX data from the SQLite DB
  3. Generates held-out probability predictions from the classifier
  4. Fits a Ridge regression (P_calibrated = Ridge.predict([P_raw]))
  5. Also fits IsotonicRegression as an alternative calibrator
  6. Saves the best calibrator as vol_spike_calibrator.pkl
"""

import os
import sys
import logging
import numpy as np

logger = logging.getLogger("geotrade.ml.vol_spike.ridge_calibrator")

MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "saved_models")
)


def train_ridge_calibrator(X_val: np.ndarray, y_val: np.ndarray, raw_probs: np.ndarray):
    """
    Trains both Ridge and Isotonic calibrators on held-out validation data.
    Picks the one with lower Brier Score.

    Args:
        X_val:      (N, 15) feature matrix — the held-out validation set
        y_val:      (N,) binary labels — 1 = vol spike occurred, 0 = calm
        raw_probs:  (N,) raw probability from vol_spike_classifier on X_val

    Returns:
        best_calibrator: fitted sklearn estimator
        brier_improvement: float (positive = calibration helped)
    """
    from sklearn.linear_model import Ridge
    from sklearn.isotonic import IsotonicRegression
    from sklearn.metrics import brier_score_loss
    import joblib

    # Brier score BEFORE calibration
    brier_raw = brier_score_loss(y_val, raw_probs)
    logger.info("Brier score (raw): %.4f", brier_raw)

    # Reshape for sklearn
    X_cal = raw_probs.reshape(-1, 1)

    # Option A: Ridge calibrator
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_cal, y_val)
    ridge_probs = np.clip(ridge.predict(X_cal), 0.0, 1.0)
    brier_ridge = brier_score_loss(y_val, ridge_probs)
    logger.info("Brier score (Ridge): %.4f", brier_ridge)

    # Option B: Isotonic regression
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(raw_probs, y_val)
    iso_probs = iso.predict(raw_probs)
    brier_iso = brier_score_loss(y_val, iso_probs)
    logger.info("Brier score (Isotonic): %.4f", brier_iso)

    # Pick best
    if brier_iso <= brier_ridge:
        best = iso
        brier_cal = brier_iso
        chosen = "Isotonic"
    else:
        best = ridge
        brier_cal = brier_ridge
        chosen = "Ridge"

    improvement = brier_raw - brier_cal
    logger.info(
        "Selected calibrator: %s | Brier improvement: %.4f",
        chosen, improvement
    )

    # Save
    os.makedirs(MODELS_DIR, exist_ok=True)
    cal_path = os.path.join(MODELS_DIR, "vol_spike_calibrator.pkl")
    joblib.dump(best, cal_path)
    logger.info("Saved calibrator to %s", cal_path)

    return best, improvement


def run_calibration_from_db():
    """
    End-to-end calibration pipeline:
      1. Load vol_spike_classifier from saved_models
      2. Pull events + outcomes from SQLite
      3. Build feature vectors
      4. Fit calibrator on held-out 20% split
      5. Save calibrator
    """
    import joblib

    clf_path = os.path.join(MODELS_DIR, "vol_spike_classifier.pkl")
    if not os.path.exists(clf_path):
        logger.error(
            "vol_spike_classifier.pkl not found at %s. "
            "Run train_vol_spike.py first.", clf_path
        )
        return

    logger.info("Loading vol_spike_classifier...")
    clf = joblib.load(clf_path)

    # Try to load events from DB
    try:
        sys.path.insert(0, os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
        ))
        from app.database.db import SessionLocal
        from app.repositories.event_repo import EventRepository
        from app.ml.vol_spike.train_vol_spike import build_training_dataset

        logger.info("Building training dataset from SQLite DB...")
        X, y, _ = build_training_dataset()

        if len(X) < 20:
            logger.warning("Insufficient events in DB for calibration (need >= 20).")
            return

        # Time-series split: last 20% = held-out validation
        split = int(len(X) * 0.8)
        X_val      = X[split:]
        y_val      = y[split:]
        raw_probs  = clf.predict_proba(X_val)[:, 1]

        train_ridge_calibrator(X_val, y_val, raw_probs)

    except Exception as exc:
        logger.error("Calibration pipeline failed: %s", exc, exc_info=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_calibration_from_db()
