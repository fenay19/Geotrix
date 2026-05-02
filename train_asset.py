"""
GeoTrade AI - Standalone Asset Model Training Script
=====================================================
This script trains a separate ML model pack for a specific asset (default: INDA).
It implements the exact improvements from Phase 1 & 2:
  1. GARCH(1,1) conditional volatility feature
  2. Directional Loss Weighting (sample weights scaled by magnitude of wrong-direction return)
  3. Early stopping on validation set to prevent overfitting
  4. Shallow trees + strong L2 regularization
  5. Label quantile thresholds computed ONLY on train split (no leakage)
  6. Feature pruning: top N features only after first XGBoost pass
  7. Confidence threshold & ensemble weights tuned on validation F1
  8. Drift + Volatility Regressors

Usage:
    python train_asset.py INDA
"""

import sys
import warnings
import os
import math
import json

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import joblib
from arch import arch_model
import torch
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
from app.ml.sequence_model import create_sequence_dataset, train_sequence_model, SequenceModel

from xgboost import XGBClassifier, XGBRegressor

try:
    from lightgbm import LGBMClassifier, LGBMRegressor
    HAS_LGBM = True
except Exception:
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
    HAS_LGBM = False

from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight, compute_class_weight
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score,
    mean_absolute_error, r2_score
)

# ── Config ────────────────────────────────────────────────────────────────────
PERIOD    = "5y"
HORIZON   = 5
BUY_Q     = 0.70   # top 30% returns = BUY
SELL_Q    = 0.30   # bottom 30% returns = SELL
TOP_N_FEATURES = 20   # keep top N after first XGBoost importance pass
SAVE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "backend", "app", "ml", "saved_models")
)
os.makedirs(SAVE_DIR, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast   = series.ewm(span=fast, adjust=False).mean()
    ema_slow   = series.ewm(span=slow, adjust=False).mean()
    macd_line  = ema_fast - ema_slow
    return macd_line - macd_line.ewm(span=signal, adjust=False).mean()

def compute_bollinger_pct(series, period=20):
    ma    = series.rolling(period).mean()
    std   = series.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    return (series - lower) / (upper - lower).replace(0, np.nan)

def compute_atr(df, period=14):
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - df["close"].shift()).abs(),
        (df["low"]  - df["close"].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def safe_div(a, b):
    return a / b.replace(0, np.nan)

# ── Feature Engineering ───────────────────────────────────────────────────────
def build_features(df, vix_df):
    f       = pd.DataFrame(index=df.index)
    close   = df["close"]
    high    = df["high"]
    low     = df["low"]
    daily_ret = close.pct_change()

    # Returns
    f["return_1d"]  = close.pct_change(1)
    f["return_2d"]  = close.pct_change(2)
    f["return_5d"]  = close.pct_change(5)
    f["return_10d"] = close.pct_change(10)
    f["return_20d"] = close.pct_change(20)
    f["return_60d"] = close.pct_change(60)

    # Volatility / ATR
    f["vol_5d"]  = daily_ret.rolling(5).std()  * math.sqrt(252)
    f["vol_20d"] = daily_ret.rolling(20).std() * math.sqrt(252)
    f["vol_60d"] = daily_ret.rolling(60).std() * math.sqrt(252)
    f["atr_14"]  = compute_atr(df, 14) / close

    # Momentum
    f["rsi_14"]        = compute_rsi(close, 14)
    f["macd_hist"]     = compute_macd(close)
    f["bollinger_pct"] = compute_bollinger_pct(close, 20)

    # Moving-average ratios
    sma20  = close.rolling(20).mean()
    sma50  = close.rolling(50).mean()
    sma100 = close.rolling(100).mean()
    sma200 = close.rolling(200).mean()
    ema20  = close.ewm(span=20, adjust=False).mean()
    ema50  = close.ewm(span=50, adjust=False).mean()

    f["sma_20_ratio"]  = close / sma20  - 1
    f["sma_50_ratio"]  = close / sma50  - 1
    f["sma_100_ratio"] = close / sma100 - 1
    f["sma_200_ratio"] = close / sma200 - 1
    f["ema_20_ratio"]  = close / ema20  - 1
    f["ema_50_ratio"]  = close / ema50  - 1

    # Cross-average trend ratios
    f["trend_20_50"]    = sma20 / sma50   - 1
    f["trend_50_100"]   = sma50 / sma100  - 1
    f["trend_50_200"]   = sma50 / sma200  - 1
    f["trend_100_200"]  = sma100 / sma200 - 1
    f["ema_sma_20_ratio"] = ema20 / sma20 - 1
    f["ema_sma_50_ratio"] = ema50 / sma50 - 1

    # Breakout / mean-reversion context
    f["dist_52w_high"] = close / close.rolling(252).max() - 1
    f["dist_52w_low"]  = close / close.rolling(252).min() - 1
    f["range_20d"]     = (high.rolling(20).max() - low.rolling(20).min()) / close
    f["range_60d"]     = (high.rolling(60).max() - low.rolling(60).min()) / close

    # Ratio features
    f["ret_5_20_ratio"]    = safe_div(f["return_5d"],  f["return_20d"].abs() + 1e-6)
    f["ret_20_60_ratio"]   = safe_div(f["return_20d"], f["return_60d"].abs() + 1e-6)
    f["vol_5_20_ratio"]    = safe_div(f["vol_5d"],  f["vol_20d"])
    f["vol_20_60_ratio"]   = safe_div(f["vol_20d"], f["vol_60d"])
    f["atr_vol_ratio"]     = safe_div(f["atr_14"],  f["vol_20d"] + 1e-6)
    f["risk_adj_ret_20d"]  = safe_div(f["return_20d"], f["vol_20d"] + 1e-6)
    f["risk_adj_ret_60d"]  = safe_div(f["return_60d"], f["vol_60d"] + 1e-6)

    # Volume
    if "volume" in df.columns:
        vol = df["volume"].replace(0, np.nan)
        f["volume_ratio_20"] = vol / vol.rolling(20).mean()
        f["volume_ratio_60"] = vol / vol.rolling(60).mean()
        f["volume_z_20"]     = (vol - vol.rolling(20).mean()) / vol.rolling(20).std()
    else:
        f["volume_ratio_20"] = 1.0
        f["volume_ratio_60"] = 1.0
        f["volume_z_20"]     = 0.0

    # VIX regime
    f = f.join(vix_df, how="left")
    f["vix"]           = f["vix"].ffill()
    f["vix_change_5d"] = f["vix"].pct_change(5)
    f["vix_change_20d"]= f["vix"].pct_change(20)
    f["vix_ma_ratio"]  = f["vix"] / f["vix"].rolling(20).mean() - 1
    f["vix_vol_ratio"] = safe_div(f["vix"] / 100.0, f["vol_20d"] + 1e-6)

    # GARCH(1,1) conditional volatility feature (regime-aware)
    try:
        ret_series = daily_ret.fillna(0.0)
        if ret_series.std() > 0.0001:
            garch_model_fit = arch_model(ret_series * 100.0, vol="Garch", p=1, q=1, dist="Normal")
            garch_res = garch_model_fit.fit(disp="off", show_warning=False)
            f["garch_sigma_1d"] = garch_res.conditional_volatility / 100.0
        else:
            f["garch_sigma_1d"] = f["vol_20d"] / math.sqrt(252.0)
    except Exception:
        f["garch_sigma_1d"] = f["vol_20d"] / math.sqrt(252.0)

    # Forward return
    f["fwd_return_5d"] = close.pct_change(HORIZON).shift(-HORIZON)
    f.dropna(inplace=True)
    return f

def main():
    symbol = "INDA"
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()

    print("=" * 70)
    print(f"GeoTrade AI - Standalone Asset Training: {symbol}")
    print(f"LightGBM available: {HAS_LGBM}")
    print(f"Save directory: {SAVE_DIR}")
    print("=" * 70)

    # Ticker resolution
    ticker_map = {
        "SP500": "^GSPC",
        "SPY": "SPY",
        "GOLD": "GC=F",
        "OIL_BRENT": "BZ=F",
        "BTCUSD": "BTC-USD",
        "INDA": "INDA",
    }
    ticker = ticker_map.get(symbol, symbol)

    print(f"Downloading price data for {ticker}...")
    try:
        df = yf.download(ticker, period=PERIOD, interval="1d", progress=False)
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
        df.dropna(inplace=True)
        if len(df) < 100:
            raise ValueError(f"Too few rows ({len(df)}) for {ticker}")
        print(f"Downloaded {len(df)} rows of data.")
    except Exception as e:
        print(f"Error downloading {ticker}: {e}")
        return

    print("Downloading VIX...")
    vix = yf.download("^VIX", period=PERIOD, interval="1d", progress=False)
    vix.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in vix.columns]
    vix = vix[["close"]].rename(columns={"close": "vix"})

    print("Engineering features...")
    data_df = build_features(df, vix)
    
    # Add raw columns temporarily for sequence normalization
    data_df["open"] = df["open"]
    data_df["high"] = df["high"]
    data_df["low"] = df["low"]
    data_df["close"] = df["close"]
    data_df["volume"] = df["volume"]
    
    # Generate sequence windows of length 30
    X_seq, _, valid_dates = create_sequence_dataset(data_df, seq_len=30, target_col="fwd_return_5d")
    
    # Align and drop raw temporary columns
    data_df = data_df.loc[valid_dates].copy()
    data_df["sequence"] = list(X_seq)
    data_df.drop(columns=["open", "high", "low", "close", "volume"], inplace=True)
    
    print(f"Engineered {len(data_df)} feature rows.")


    BASE_FEATURES = [
        "return_1d","return_2d","return_5d","return_10d","return_20d","return_60d",
        "vol_5d","vol_20d","vol_60d","atr_14",
        "rsi_14","macd_hist","bollinger_pct",
        "sma_20_ratio","sma_50_ratio","sma_100_ratio","sma_200_ratio",
        "ema_20_ratio","ema_50_ratio",
        "trend_20_50","trend_50_100","trend_50_200","trend_100_200",
        "ema_sma_20_ratio","ema_sma_50_ratio",
        "dist_52w_high","dist_52w_low","range_20d","range_60d",
        "ret_5_20_ratio","ret_20_60_ratio",
        "vol_5_20_ratio","vol_20_60_ratio","atr_vol_ratio",
        "risk_adj_ret_20d","risk_adj_ret_60d",
        "volume_ratio_20","volume_ratio_60","volume_z_20",
        "vix","vix_change_5d","vix_change_20d","vix_ma_ratio","vix_vol_ratio",
        "garch_sigma_1d",
    ]
    FEATURE_COLS = BASE_FEATURES
    print(f"Total features: {len(FEATURE_COLS)}")

    # Time series split
    n = len(data_df)
    train_end = int(n * 0.70)
    valid_end = int(n * 0.80)

    train_df = data_df.iloc[:train_end].copy()
    valid_df = data_df.iloc[train_end:valid_end].copy()
    test_df  = data_df.iloc[valid_end:].copy()

    # Quantile label thresholds computed strictly on train split
    sell_threshold = train_df["fwd_return_5d"].quantile(SELL_Q)
    buy_threshold  = train_df["fwd_return_5d"].quantile(BUY_Q)
    print(f"\nLabel Thresholds:")
    print(f"  SELL if fwd_return_5d <= {sell_threshold:.4f}")
    print(f"  BUY  if fwd_return_5d >= {buy_threshold:.4f}")

    def apply_labels(d):
        d = d.copy()
        d["label"] = "HOLD"
        d.loc[d["fwd_return_5d"] <= sell_threshold, "label"] = "SELL"
        d.loc[d["fwd_return_5d"] >= buy_threshold,  "label"] = "BUY"
        return d

    train_df = apply_labels(train_df)
    valid_df = apply_labels(valid_df)
    test_df  = apply_labels(test_df)

    print(f"\nTrain: {len(train_df)} | Valid: {len(valid_df)} | Test: {len(test_df)}")
    print("Train label distribution:", train_df["label"].value_counts().to_dict())

    # Label encoding
    le = LabelEncoder()
    y_train_cls = le.fit_transform(train_df["label"])
    y_valid_cls = le.transform(valid_df["label"])
    y_test_cls  = le.transform(test_df["label"])

    y_train_drift = train_df["fwd_return_5d"] * (252 / HORIZON)
    y_valid_drift = valid_df["fwd_return_5d"] * (252 / HORIZON)
    y_test_drift  = test_df["fwd_return_5d"]  * (252 / HORIZON)

    y_train_vol   = train_df["vol_20d"]
    y_valid_vol   = valid_df["vol_20d"]
    y_test_vol    = test_df["vol_20d"]

    # Outlier clipping
    X_train_raw = train_df[FEATURE_COLS].copy()
    X_valid_raw = valid_df[FEATURE_COLS].copy()
    X_test_raw  = test_df[FEATURE_COLS].copy()

    clip_low  = X_train_raw.quantile(0.01)
    clip_high = X_train_raw.quantile(0.99)
    train_med = X_train_raw.median()

    def clip_features(X):
        Xc = X.copy().clip(lower=clip_low, upper=clip_high, axis=1)
        Xc = Xc.replace([np.inf, -np.inf], np.nan).fillna(train_med)
        return Xc

    X_train = clip_features(X_train_raw)
    X_valid = clip_features(X_valid_raw)
    X_test  = clip_features(X_test_raw)

    # ── Train PyTorch Sequence Classifier ─────────────────────────────────────────
    X_train_seq = np.array(train_df["sequence"].tolist(), dtype=np.float32)
    X_valid_seq = np.array(valid_df["sequence"].tolist(), dtype=np.float32)
    X_test_seq  = np.array(test_df["sequence"].tolist(), dtype=np.float32)

    print("\n" + "=" * 70)
    print("STEP 0.5: Training PyTorch CNN-BiGRU-Attention Sequence model...")
    print("=" * 70)
    torch_model = train_sequence_model(
        X_train_seq, y_train_cls, X_valid_seq, y_valid_cls, 
        num_classes=3, epochs=25, batch_size=64
    )

    # Save PyTorch sequence model state dict
    torch.save(torch_model.state_dict(), f"{SAVE_DIR}/{symbol}_sequence_model.pkl")
    print(f"Saved PyTorch sequence model to: {SAVE_DIR}/{symbol}_sequence_model.pkl")

    # Generate embeddings (evaluation mode)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch_model = torch_model.to(device)
    torch_model.eval()

    with torch.no_grad():
        train_embeddings = torch_model(torch.tensor(X_train_seq).to(device)).cpu().numpy()
        valid_embeddings = torch_model(torch.tensor(X_valid_seq).to(device)).cpu().numpy()
        test_embeddings  = torch_model(torch.tensor(X_test_seq).to(device)).cpu().numpy()

    # Concatenate embeddings as new features
    emb_cols = [f"seq_emb_{i}" for i in range(16)]
    train_emb_df = pd.DataFrame(train_embeddings, columns=emb_cols, index=train_df.index)
    valid_emb_df = pd.DataFrame(valid_embeddings, columns=emb_cols, index=valid_df.index)
    test_emb_df  = pd.DataFrame(test_embeddings,  columns=emb_cols, index=test_df.index)

    X_train = pd.concat([X_train, train_emb_df], axis=1)
    X_valid = pd.concat([X_valid, valid_emb_df], axis=1)
    X_test  = pd.concat([X_test,  test_emb_df],  axis=1)

    # Append to FEATURE_COLS
    FEATURE_COLS = list(FEATURE_COLS) + emb_cols


    # Class Weights and Directional Loss Penalty
    sample_weights = compute_sample_weight(class_weight="balanced", y=y_train_cls)
    direction_multiplier = 3.0
    buy_idx = list(le.classes_).index("BUY")
    sell_idx = list(le.classes_).index("SELL")

    for i in range(len(train_df)):
        actual_fwd_ret = train_df["fwd_return_5d"].iloc[i]
        label_cls = y_train_cls[i]
        
        if label_cls == buy_idx and actual_fwd_ret < 0:
            sample_weights[i] *= (1.0 + abs(actual_fwd_ret) * direction_multiplier)
        elif label_cls == sell_idx and actual_fwd_ret > 0:
            sample_weights[i] *= (1.0 + abs(actual_fwd_ret) * direction_multiplier)

    valid_weights  = compute_sample_weight(class_weight="balanced", y=y_valid_cls)
    class_weights  = compute_class_weight(
        class_weight="balanced",
        classes=np.unique(y_train_cls),
        y=y_train_cls,
    )
    class_weight_dict = dict(zip(np.unique(y_train_cls), class_weights))

    # XGBoost hyperparameter search with Early Stopping
    print("\nSTEP 1: Training XGBoost with early stopping & regularization...")
    XGB_PARAMS = [
        {
            "max_depth": 1, "learning_rate": 0.01, "n_estimators": 3000,
            "min_child_weight": 20, "reg_lambda": 10.0,
            "subsample": 0.75, "colsample_bytree": 0.75, "gamma": 0.3,
        },
        {
            "max_depth": 2, "learning_rate": 0.01, "n_estimators": 2000,
            "min_child_weight": 20, "reg_lambda": 20.0,
            "subsample": 0.70, "colsample_bytree": 0.70, "gamma": 0.5,
        },
        {
            "max_depth": 2, "learning_rate": 0.02, "n_estimators": 2000,
            "min_child_weight": 30, "reg_lambda": 10.0,
            "subsample": 0.75, "colsample_bytree": 0.75, "gamma": 0.3,
        },
    ]

    best_xgb, best_xgb_score, best_xgb_params = None, -1, None
    for params in XGB_PARAMS:
        model = XGBClassifier(
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=-1,
            tree_method="hist",
            early_stopping_rounds=40,
            **params,
        )
        model.fit(
            X_train, y_train_cls,
            sample_weight=sample_weights,
            eval_set=[(X_valid, y_valid_cls)],
            sample_weight_eval_set=[valid_weights],
            verbose=False,
        )
        pred  = model.predict(X_valid)
        score = f1_score(y_valid_cls, pred, average="macro")
        best_n = model.best_iteration if hasattr(model, "best_iteration") else "N/A"
        print(f"  depth={params['max_depth']} lr={params['learning_rate']} L2={params['reg_lambda']} | stopped at tree #{best_n} | Val F1={score:.4f}")
        if score > best_xgb_score:
            best_xgb_score  = score
            best_xgb        = model
            best_xgb_params = params

    clf_xgb = best_xgb
    print(f"Best XGBoost Val macro F1: {best_xgb_score:.4f}")

    # Feature Pruning
    print(f"\nSTEP 2: Feature pruning - keeping top {TOP_N_FEATURES} features...")
    importances = pd.Series(clf_xgb.feature_importances_, index=FEATURE_COLS)
    top_features = importances.nlargest(TOP_N_FEATURES).index.tolist()
    print("Top features:", top_features)

    X_train_p = X_train[top_features]
    X_valid_p = X_valid[top_features]
    X_test_p  = X_test[top_features]

    clf_xgb_p = XGBClassifier(
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
        early_stopping_rounds=40,
        **best_xgb_params,
    )
    clf_xgb_p.fit(
        X_train_p, y_train_cls,
        sample_weight=sample_weights,
        eval_set=[(X_valid_p, y_valid_cls)],
        sample_weight_eval_set=[valid_weights],
        verbose=False,
    )
    pruned_val_score = f1_score(y_valid_cls, clf_xgb_p.predict(X_valid_p), average="macro")
    print(f"XGBoost full features Val F1 : {best_xgb_score:.4f}")
    print(f"XGBoost pruned features Val F1: {pruned_val_score:.4f}")

    if pruned_val_score >= best_xgb_score - 0.03:
        clf_xgb    = clf_xgb_p
        FEATURE_COLS = top_features
        X_train    = X_train_p
        X_valid    = X_valid_p
        X_test     = X_test_p
        print(f"Using PRUNED feature set ({TOP_N_FEATURES} features)")
    else:
        print("Pruned model significantly worse -- keeping full feature set")

    # Second Model (LightGBM)
    print("\nSTEP 3: Training second ensemble model (LightGBM/HistGB)...")
    if HAS_LGBM:
        LGBM_PARAMS = [
            {
                "max_depth": 1, "num_leaves": 2, "learning_rate": 0.01, "n_estimators": 2000,
                "min_child_samples": 20, "reg_lambda": 10.0, "subsample": 0.75, "colsample_bytree": 0.75
            },
            {
                "max_depth": 2, "num_leaves": 4, "learning_rate": 0.01, "n_estimators": 2000,
                "min_child_samples": 20, "reg_lambda": 20.0, "subsample": 0.70, "colsample_bytree": 0.70
            },
        ]
        best_lgbm, best_lgbm_score = None, -1
        for params in LGBM_PARAMS:
            model = LGBMClassifier(
                objective="multiclass",
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
                verbose=-1,
                **params,
            )
            model.fit(
                X_train, y_train_cls,
                eval_set=[(X_valid, y_valid_cls)],
                callbacks=[__import__("lightgbm").early_stopping(40, verbose=False)],
            )
            pred = model.predict(X_valid)
            score = f1_score(y_valid_cls, pred, average="macro")
            if score > best_lgbm_score:
                best_lgbm_score = score
                best_lgbm = model
        clf_lgbm = best_lgbm
    else:
        clf_lgbm = HistGradientBoostingClassifier(
            max_iter=500,
            learning_rate=0.01,
            max_leaf_nodes=4,
            min_samples_leaf=50,
            l2_regularization=20.0,
            class_weight=class_weight_dict,
            random_state=42,
        )
        clf_lgbm.fit(X_train, y_train_cls)

    lgbm_val_score = f1_score(y_valid_cls, clf_lgbm.predict(X_valid), average="macro")
    print(f"Second model Val F1: {lgbm_val_score:.4f}")

    # Ensemble Weight and Threshold Tuning
    print("\nSTEP 4: Tuning ensemble weights and confidence threshold...")
    best_ens_score, best_w, best_thresh = -1, 1.0, 0.0
    weight_range = [0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0]
    thresh_range = [0.0, 0.35, 0.38, 0.40, 0.42, 0.45, 0.48, 0.50, 0.52]

    for w in weight_range:
        probs = w * clf_xgb.predict_proba(X_valid) + (1 - w) * clf_lgbm.predict_proba(X_valid)
        for thresh in thresh_range:
            raw      = probs.argmax(axis=1)
            conf     = probs.max(axis=1)
            hold_id  = list(le.classes_).index("HOLD")
            filtered = raw.copy()
            filtered[conf < thresh] = hold_id
            
            # Constraint: hold conversions shouldn't exceed 15% of validation set
            if (conf < thresh).mean() > 0.15:
                continue
                
            score = f1_score(y_valid_cls, filtered, average="macro")
            if score > best_ens_score:
                best_ens_score = score
                best_w         = w
                best_thresh    = thresh

    XGB_W    = best_w
    LGBM_W   = 1 - best_w
    CONF_THR = best_thresh
    print(f"Weights -> XGB: {XGB_W:.2f} | LGBM: {LGBM_W:.2f} | Threshold: {CONF_THR:.2f}")

    # Final Evaluations
    def evaluate(X, y_true, name):
        probs    = XGB_W * clf_xgb.predict_proba(X) + LGBM_W * clf_lgbm.predict_proba(X)
        raw      = probs.argmax(axis=1)
        conf     = probs.max(axis=1)
        hold_id  = list(le.classes_).index("HOLD")
        filtered = raw.copy()
        filtered[conf < CONF_THR] = hold_id
        score = f1_score(y_true, filtered, average="macro")
        print(f"\n{name} Split Evaluation:")
        print(classification_report(y_true, filtered, target_names=le.classes_))
        return score

    train_f1 = evaluate(X_train, y_train_cls, "Train")
    val_f1   = evaluate(X_valid, y_valid_cls, "Validation")
    test_f1  = evaluate(X_test,  y_test_cls,  "Test")

    # Regressors
    print("\nSTEP 5: Training Drift + Volatility Regressors...")
    drift_reg = XGBRegressor(
        n_estimators=1000, max_depth=3, learning_rate=0.01,
        subsample=0.75, colsample_bytree=0.75, reg_lambda=20.0,
        random_state=42, n_jobs=-1, tree_method="hist",
        early_stopping_rounds=40,
    )
    drift_reg.fit(X_train, y_train_drift, eval_set=[(X_valid, y_valid_drift)], verbose=False)

    vol_reg = XGBRegressor(
        n_estimators=1000, max_depth=3, learning_rate=0.01,
        subsample=0.75, colsample_bytree=0.75, reg_lambda=20.0,
        random_state=42, n_jobs=-1, tree_method="hist",
        early_stopping_rounds=40,
    )
    vol_reg.fit(X_train, y_train_vol, eval_set=[(X_valid, y_valid_vol)], verbose=False)

    drift_mae = mean_absolute_error(y_test_drift, drift_reg.predict(X_test))
    vol_mae   = mean_absolute_error(y_test_vol,   vol_reg.predict(X_test))
    print(f"Drift Regressor - Test MAE: {drift_mae:.4f}")
    print(f"Vol Regressor   - Test MAE: {vol_mae:.4f}")

    # Save binaries
    print(f"\nSaving {symbol} artifacts to {SAVE_DIR}...")
    joblib.dump(clf_xgb,   f"{SAVE_DIR}/{symbol}_signal_classifier.pkl")
    joblib.dump(clf_lgbm,  f"{SAVE_DIR}/{symbol}_second_signal_classifier.pkl")
    joblib.dump(drift_reg, f"{SAVE_DIR}/{symbol}_drift_regressor.pkl")
    joblib.dump(vol_reg,   f"{SAVE_DIR}/{symbol}_vol_regressor.pkl")
    joblib.dump(le,        f"{SAVE_DIR}/{symbol}_label_encoder.pkl")
    joblib.dump(FEATURE_COLS, f"{SAVE_DIR}/{symbol}_feature_cols.pkl")
    joblib.dump(clip_low,  f"{SAVE_DIR}/{symbol}_clip_low.pkl")
    joblib.dump(clip_high, f"{SAVE_DIR}/{symbol}_clip_high.pkl")
    joblib.dump(train_med, f"{SAVE_DIR}/{symbol}_train_median.pkl")

    metadata = {
        "model_type": "standalone_xgboost_lgbm_ensemble",
        "xgb_weight": XGB_W,
        "second_model_weight": LGBM_W,
        "confidence_threshold": CONF_THR,
        "label_classes": list(le.classes_),
        "horizon_days": HORIZON,
        "buy_quantile": BUY_Q,
        "sell_quantile": SELL_Q,
        "feature_count": len(FEATURE_COLS),
        "train_f1": round(train_f1, 4),
        "val_f1": round(val_f1, 4),
        "test_f1": round(test_f1, 4),
    }
    joblib.dump(metadata, f"{SAVE_DIR}/{symbol}_ensemble_metadata.pkl")
    print(json.dumps(metadata, indent=2))
    print(f"Standalone artifacts successfully compiled and saved.")

if __name__ == "__main__":
    main()
