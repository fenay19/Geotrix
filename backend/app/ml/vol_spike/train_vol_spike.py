"""
Vol-Spike Training Script
==========================
Offline training pipeline for the XGBoost + LightGBM Vol-Spike ensemble.

What it does:
  1. Downloads 2y of VIX + price history for tracked assets from yfinance
  2. Loads historical geopolitical events from the SQLite DB (app_sql.db)
  3. Labels each event: "SPIKE" if |price change in 5d| > 1 stdev, else "CALM"
  4. Builds 15-feature vectors via VolSpikeFeatureBuilder
  5. Trains XGBoost BinaryClassifier (vol_spike_prob)
  6. Trains LightGBM Regressor (vol_spike_magnitude)
  7. Saves all to backend/app/ml/saved_models/vol_spike_*.pkl

Run from project root:
    python -m backend.app.ml.vol_spike.train_vol_spike

Or after cd into backend/:
    python -m app.ml.vol_spike.train_vol_spike
"""

import os
import sys
import logging
import numpy as np
import pandas as pd
import yfinance as yf
import joblib

logger = logging.getLogger("geotrade.ml.vol_spike.train")
logging.basicConfig(level=logging.INFO)

# ── Paths ─────────────────────────────────────────────────────────────────────
THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", "..", "..", ".."))
MODELS_DIR  = os.path.abspath(os.path.join(THIS_DIR, "..", "saved_models"))
os.makedirs(MODELS_DIR, exist_ok=True)

sys.path.insert(0, BACKEND_DIR)

# ── Asset tickers for price lookups ──────────────────────────────────────────
ASSET_TICKERS = {
    "SP500":        "^GSPC",
    "GOLD":         "GC=F",
    "OIL_BRENT":    "BZ=F",
    "BTCUSD":       "BTC-USD",
    "TECH":         "QQQ",
    "BONDS":        "TLT",
    "DOLLAR":       "UUP",
    "EM_EQUITY":    "EEM",
    "INDIA_EQUITY": "INDA",
    "GOLD_ETF":     "GLD",
}


def _fetch_price_history() -> dict:
    """Downloads 2y of daily OHLC for all tracked assets."""
    price_data = {}
    for asset, ticker in ASSET_TICKERS.items():
        try:
            df = yf.download(ticker, period="2y", interval="1d", progress=False)
            df.columns = [
                c[0].lower() if isinstance(c, tuple) else c.lower()
                for c in df.columns
            ]
            df = df[["open", "high", "low", "close", "volume"]].dropna()
            df.index = df.index.tz_localize(None) if df.index.tzinfo else df.index
            price_data[asset] = df
            logger.info("  Fetched %d rows for %s (%s)", len(df), asset, ticker)
        except Exception as exc:
            logger.warning("  Failed to fetch %s: %s", ticker, exc)
    return price_data


def _compute_realized_vol(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Annualized rolling volatility."""
    import math
    return df["close"].pct_change().rolling(window).std() * math.sqrt(252)


def build_training_dataset():
    """
    Loads events from DB, matches them to price series, labels spikes.

    Returns:
        X: np.ndarray (N, 15) feature matrix
        y: np.ndarray (N,)    binary labels (1=SPIKE, 0=CALM)
        y_mag: np.ndarray (N,) magnitude values (5-day return)
    """
    from app.database.db import SessionLocal
    from app.repositories.event_repo import EventRepository
    from app.ml.vol_spike.feature_builder import vol_spike_feature_builder

    logger.info("Loading events from SQLite DB...")
    db = SessionLocal()
    try:
        event_repo = EventRepository(db)
        events = event_repo.get_all(skip=0, limit=10000)
        logger.info("  Found %d events in DB.", len(events))
    finally:
        db.close()

    if not events:
        logger.error("No events found in DB. Seed the DB before training.")
        return np.array([]), np.array([]), np.array([])

    # Fetch price history for labelling
    logger.info("Fetching price history from yfinance...")
    price_data = _fetch_price_history()

    # Fetch VIX
    try:
        vix_df = yf.download("^VIX", period="2y", interval="1d", progress=False)
        vix_df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in vix_df.columns]
        vix_df.index = vix_df.index.tz_localize(None) if vix_df.index.tzinfo else vix_df.index
        vix_series = vix_df["close"].dropna()
    except Exception:
        vix_series = pd.Series(dtype=float)

    X_rows = []
    y_rows = []
    y_mag_rows = []

    for event in events:
        try:
            event_date = pd.Timestamp(event.timestamp or event.created_at)
            if pd.isna(event_date):
                continue
            event_date = event_date.tz_localize(None) if event_date.tzinfo else event_date
            event_date = event_date.normalize()

            # Match event to asset category via country — default SP500
            asset_cat = "SP500"
            price_df  = price_data.get(asset_cat)
            if price_df is None or price_df.empty:
                continue

            # Realized vol at event date (20d rolling)
            rv = _compute_realized_vol(price_df)
            rv_at_date = rv.asof(event_date) if not rv.empty else 0.15
            rv_at_date = rv_at_date if not np.isnan(rv_at_date) else 0.15

            # 5-day forward return
            price_at_date  = price_df["close"].asof(event_date)
            price_5d_later = price_df["close"].asof(event_date + pd.Timedelta(days=7))

            if pd.isna(price_at_date) or pd.isna(price_5d_later) or price_at_date == 0:
                continue

            fwd_ret = abs((price_5d_later - price_at_date) / price_at_date)
            daily_sigma = rv_at_date / (252 ** 0.5)
            # Use 2-sigma threshold for 5-day return label
            label = 1 if fwd_ret > daily_sigma * 2.0 else 0  # 2-sigma threshold

            # VIX at event date
            vix_val = float(vix_series.asof(event_date)) if not vix_series.empty else 15.0
            vix_val = vix_val if not np.isnan(vix_val) else 15.0

            # GARCH approx = rv / sqrt(252)
            garch = rv_at_date / (252 ** 0.5)

            # dist_52w_high
            d52 = float(price_df["close"].rolling(252).apply(
                lambda x: x.iloc[-1] / x.max() - 1
            ).asof(event_date) or 0.0)

            feat = vol_spike_feature_builder.build(
                event_type               = event.event_type or "policy",
                severity                 = float(event.severity or 5),
                escalation_potential     = float(event.escalation_potential or 2),
                sentiment_signed         = 0.0,
                nlp_confidence           = 0.7,
                country_risk_score       = 50.0,
                gti_score                = 50.0,
                casualties               = float(event.casualties or 0),
                econ_damage_million_usd  = float(event.economic_damage or 0.0),
                vix                      = vix_val,
                vol_20d                  = rv_at_date,
                garch_sigma_1d           = garch,
                dist_52w_high            = d52,
                asset_category           = asset_cat,
            )
            X_rows.append(feat)
            y_rows.append(label)
            y_mag_rows.append(fwd_ret)

        except Exception as exc:
            logger.warning("Skipping event %s: %s", getattr(event, "id", "?"), exc)

    if not X_rows:
        logger.error("Could not build any training samples from DB events.")
        return np.array([]), np.array([]), np.array([])

    X = np.stack(X_rows).astype(np.float32)
    y = np.array(y_rows, dtype=np.int32)
    y_mag = np.array(y_mag_rows, dtype=np.float32)
    logger.info(
        "Dataset built: %d samples | SPIKE: %d | CALM: %d",
        len(y), int(y.sum()), int((y == 0).sum())
    )
    return X, y, y_mag


def train():
    """Main training function."""
    from xgboost import XGBClassifier
    import lightgbm as lgb
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, brier_score_loss

    logger.info("=== Vol-Spike Ensemble Training ===")
    X, y, y_mag = build_training_dataset()

    if len(X) < 10:
        logger.error("Not enough training samples (< 10). Cannot train.")
        return

    X_train, X_val, y_train, y_val, y_mag_train, y_mag_val = train_test_split(
        X, y, y_mag, test_size=0.2, shuffle=False  # time-series: no shuffle
    )
    logger.info("Train: %d | Val: %d", len(X_train), len(X_val))

    # ── 1. XGBoost Binary Classifier ──────────────────────────────────────
    logger.info("Training XGBoost vol-spike classifier...")
    scale_pos = max(1.0, float((y_train == 0).sum()) / float((y_train == 1).sum() + 1e-6))
    xgb_clf = XGBClassifier(
        n_estimators    = 200,
        max_depth       = 4,
        learning_rate   = 0.05,
        subsample       = 0.8,
        colsample_bytree= 0.8,
        scale_pos_weight= scale_pos,
        use_label_encoder=False,
        eval_metric     = "logloss",
        n_jobs          = -1,
        random_state    = 42,
    )
    xgb_clf.fit(X_train, y_train)
    xgb_probs = xgb_clf.predict_proba(X_val)[:, 1]
    logger.info("XGBoost Brier Score: %.4f", brier_score_loss(y_val, xgb_probs))

    # ── 2. LightGBM Magnitude Regressor (predict |Δprice| / sigma) ────────
    logger.info("Training LightGBM magnitude regressor...")
    lgb_reg = lgb.LGBMRegressor(
        n_estimators  = 200,
        max_depth     = 4,
        learning_rate = 0.05,
        subsample     = 0.8,
        n_jobs        = -1,
        random_state  = 42,
        verbose       = -1,
    )
    lgb_reg.fit(X_train, y_mag_train)

    # ── 3. Ridge Calibrator ────────────────────────────────────────────────
    from app.ml.vol_spike.ridge_calibrator import train_ridge_calibrator
    train_ridge_calibrator(X_val, y_val, xgb_probs)

    # ── 4. Save models ─────────────────────────────────────────────────────
    logger.info("Saving models to %s...", MODELS_DIR)
    joblib.dump(xgb_clf, os.path.join(MODELS_DIR, "vol_spike_classifier.pkl"))
    joblib.dump(lgb_reg, os.path.join(MODELS_DIR, "vol_spike_magnitude.pkl"))
    logger.info("vol_spike_classifier.pkl and vol_spike_magnitude.pkl saved.")

    # Report
    preds = (xgb_probs >= 0.55).astype(int)
    try:
        logger.info("\n%s", classification_report(y_val, preds, labels=[0, 1], target_names=["CALM", "SPIKE"], zero_division=0))
    except Exception as exc:
        logger.warning("Could not generate classification report: %s", exc)


if __name__ == "__main__":
    train()
