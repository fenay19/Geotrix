"""
GeoTrade AI - Full Model Evaluation Suite (Phase 4)
=====================================================
Evaluates the Universal ensemble + per-asset Platt calibrators.
Phase 4: individual asset models are deprecated — all inference uses Universal.

Usage:
    python evaluate_all.py
"""

import os
import sys
import warnings
import math
import numpy as np
import pandas as pd
import yfinance as yf
import joblib
import torch

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "backend", "app", "ml", "saved_models")
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from sklearn.metrics import (
    classification_report, f1_score, accuracy_score, confusion_matrix
)
from arch import arch_model
from app.ml.sequence_model import create_sequence_dataset, SequenceModel

PERIOD  = "5y"
HORIZON = 5

INDIVIDUAL_ASSETS = {
    "GOLD":      "GC=F",
    "OIL_BRENT": "BZ=F",
    "SP500":     "^GSPC",
    "BTCUSD":    "BTC-USD",
    "INDA":      "INDA",
}

# Universal uses a multi-asset pool; we proxy with a representative asset per class
UNIVERSAL_ASSETS = {
    "SP500":         "^GSPC",
    "CHINA_EQUITY":  "MCHI",
    "INDIA_EQUITY":  "INDA",
    "EUROPE_EQUITY": "VGK",
    "JAPAN_EQUITY":  "EWJ",
    "BRAZIL_EQUITY": "EWZ",
    "GOLD":          "GC=F",
    "OIL_BRENT":     "BZ=F",
    "BTCUSD":        "BTC-USD",
    "EM_EQUITY":     "EEM",
    "GOLD_ETF":      "GLD",
    "BONDS":         "TLT",
    "DOLLAR":        "UUP",
    "TECH":          "QQQ",
}

# ── Technical Indicators ──────────────────────────────────────────────────────
def compute_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast  = series.ewm(span=fast, adjust=False).mean()
    ema_slow  = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
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

# ── Feature Builder ───────────────────────────────────────────────────────────
def build_features(df, vix_df, ticker_symbol):
    f = pd.DataFrame(index=df.index)
    close     = df["close"]
    high      = df["high"]
    low       = df["low"]
    daily_ret = close.pct_change()

    f["return_1d"]  = close.pct_change(1)
    f["return_2d"]  = close.pct_change(2)
    f["return_5d"]  = close.pct_change(5)
    f["return_10d"] = close.pct_change(10)
    f["return_20d"] = close.pct_change(20)
    f["return_60d"] = close.pct_change(60)

    f["vol_5d"]  = daily_ret.rolling(5).std()  * math.sqrt(252)
    f["vol_20d"] = daily_ret.rolling(20).std() * math.sqrt(252)
    f["vol_60d"] = daily_ret.rolling(60).std() * math.sqrt(252)
    f["atr_14"]  = compute_atr(df, 14) / close

    f["rsi_14"]        = compute_rsi(close, 14)
    f["macd_hist"]     = compute_macd(close)
    f["bollinger_pct"] = compute_bollinger_pct(close, 20)

    sma20  = close.rolling(20).mean()
    sma50  = close.rolling(50).mean()
    sma100 = close.rolling(100).mean()
    sma200 = close.rolling(200).mean()
    ema20  = close.ewm(span=20, adjust=False).mean()
    ema50  = close.ewm(span=50, adjust=False).mean()

    f["sma_20_ratio"]    = close / sma20  - 1
    f["sma_50_ratio"]    = close / sma50  - 1
    f["sma_100_ratio"]   = close / sma100 - 1
    f["sma_200_ratio"]   = close / sma200 - 1
    f["ema_20_ratio"]    = close / ema20  - 1
    f["ema_50_ratio"]    = close / ema50  - 1
    f["trend_20_50"]     = sma20 / sma50   - 1
    f["trend_50_100"]    = sma50 / sma100  - 1
    f["trend_50_200"]    = sma50 / sma200  - 1
    f["trend_100_200"]   = sma100 / sma200 - 1
    f["ema_sma_20_ratio"] = ema20 / sma20  - 1
    f["ema_sma_50_ratio"] = ema50 / sma50  - 1

    f["dist_52w_high"] = close / close.rolling(252).max() - 1
    f["dist_52w_low"]  = close / close.rolling(252).min() - 1
    f["range_20d"]     = (high.rolling(20).max() - low.rolling(20).min()) / close
    f["range_60d"]     = (high.rolling(60).max() - low.rolling(60).min()) / close

    f["ret_5_20_ratio"]   = safe_div(f["return_5d"],  f["return_20d"].abs() + 1e-6)
    f["ret_20_60_ratio"]  = safe_div(f["return_20d"], f["return_60d"].abs() + 1e-6)
    f["vol_5_20_ratio"]   = safe_div(f["vol_5d"],  f["vol_20d"])
    f["vol_20_60_ratio"]  = safe_div(f["vol_20d"], f["vol_60d"])
    f["atr_vol_ratio"]    = safe_div(f["atr_14"],  f["vol_20d"] + 1e-6)
    f["risk_adj_ret_20d"] = safe_div(f["return_20d"], f["vol_20d"] + 1e-6)
    f["risk_adj_ret_60d"] = safe_div(f["return_60d"], f["vol_60d"] + 1e-6)

    if "volume" in df.columns:
        vol = df["volume"].replace(0, np.nan)
        f["volume_ratio_20"] = vol / vol.rolling(20).mean()
        f["volume_ratio_60"] = vol / vol.rolling(60).mean()
        f["volume_z_20"]     = (vol - vol.rolling(20).mean()) / vol.rolling(20).std()
    else:
        f["volume_ratio_20"] = 1.0
        f["volume_ratio_60"] = 1.0
        f["volume_z_20"]     = 0.0

    f = f.join(vix_df, how="left")
    f["vix"]            = f["vix"].ffill()
    f["vix_change_5d"]  = f["vix"].pct_change(5)
    f["vix_change_20d"] = f["vix"].pct_change(20)
    f["vix_ma_ratio"]   = f["vix"] / f["vix"].rolling(20).mean() - 1
    f["vix_vol_ratio"]  = safe_div(f["vix"] / 100.0, f["vol_20d"] + 1e-6)

    try:
        ret_series = daily_ret.fillna(0.0)
        if ret_series.std() > 0.0001:
            garch_fit = arch_model(ret_series * 100.0, vol="Garch", p=1, q=1, dist="Normal")
            garch_res = garch_fit.fit(disp="off", show_warning=False)
            f["garch_sigma_1d"] = garch_res.conditional_volatility / 100.0
        else:
            f["garch_sigma_1d"] = f["vol_20d"] / math.sqrt(252.0)
    except Exception:
        f["garch_sigma_1d"] = f["vol_20d"] / math.sqrt(252.0)

    # Asset dummies (Phase 4: expanded to 14-asset categories)
    SYMBOL_TO_ASSET = {
        "SPY": "SP500", "^GSPC": "SP500", "SP500": "SP500",
        "MCHI": "CHINA_EQUITY", "INDA": "INDIA_EQUITY",
        "VGK": "EUROPE_EQUITY", "EWJ": "JAPAN_EQUITY", "EWZ": "BRAZIL_EQUITY",
        "GC=F": "GOLD", "GOLD": "GOLD",
        "BZ=F": "OIL_BRENT", "OIL_BRENT": "OIL_BRENT",
        "BTC-USD": "BTCUSD", "BTCUSD": "BTCUSD",
        "EEM": "EM_EQUITY", "GLD": "GOLD_ETF", "TLT": "BONDS",
        "UUP": "DOLLAR",   "QQQ": "TECH",
    }
    current_asset = SYMBOL_TO_ASSET.get(ticker_symbol, "SP500")
    for asset_key in set(SYMBOL_TO_ASSET.values()):
        f[f"asset_{asset_key}"] = 1.0 if current_asset == asset_key else 0.0

    # Phase 4: 8 new SELL-friendly features
    rsi14    = compute_rsi(close, 14)
    rsi_min  = rsi14.rolling(14).min()
    rsi_max  = rsi14.rolling(14).max()
    stoch_k  = (rsi14 - rsi_min) / (rsi_max - rsi_min + 1e-6)
    f["stoch_rsi"]  = stoch_k.rolling(3).mean()
    f["rsi_div"]    = rsi14 - rsi14.rolling(10).mean()

    vol_col = df["volume"].replace(0, np.nan) if "volume" in df.columns else pd.Series(1.0, index=df.index)
    mf_vol  = ((close - low) - (high - close)) / (high - low + 1e-6) * vol_col
    f["cmf_20"]        = mf_vol.rolling(20).sum() / vol_col.rolling(20).sum()
    f["drawdown_20d"]  = close / close.rolling(20).max() - 1
    f["drawdown_60d"]  = close / close.rolling(60).max() - 1

    vix_col = f.get("vix", pd.Series(15.0, index=df.index))
    vol20   = f.get("vol_20d", pd.Series(0.15, index=df.index))
    f["regime_flag"]    = ((vix_col > 20) & (vol20 > 0.20)).astype(float)
    f["trend_strength"] = f["sma_20_ratio"].abs() + f["sma_50_ratio"].abs()
    f["fwd_return_10d"] = close.pct_change(HORIZON * 2).shift(-(HORIZON * 2))

    f["fwd_return_5d"] = close.pct_change(HORIZON).shift(-HORIZON)
    f.dropna(inplace=True)
    return f


def load_model_pack(symbol):
    """Load all model artifacts for a given symbol."""
    def p(suffix):
        return os.path.join(SAVE_DIR, f"{symbol}_{suffix}.pkl")

    required = ["signal_classifier", "drift_regressor", "vol_regressor",
                "label_encoder", "feature_cols"]
    for r in required:
        if not os.path.exists(p(r)):
            raise FileNotFoundError(f"Missing {symbol}_{r}.pkl in {SAVE_DIR}")

    pack = {
        "clf":          joblib.load(p("signal_classifier")),
        "drift_reg":    joblib.load(p("drift_regressor")),
        "vol_reg":      joblib.load(p("vol_regressor")),
        "le":           joblib.load(p("label_encoder")),
        "feature_cols": joblib.load(p("feature_cols")),
        "second_clf":   joblib.load(p("second_signal_classifier")) if os.path.exists(p("second_signal_classifier")) else None,
        "metadata":     joblib.load(p("ensemble_metadata"))         if os.path.exists(p("ensemble_metadata")) else None,
        "clip_low":     joblib.load(p("clip_low"))                  if os.path.exists(p("clip_low"))           else None,
        "clip_high":    joblib.load(p("clip_high"))                 if os.path.exists(p("clip_high"))          else None,
        "train_median": joblib.load(p("train_median"))              if os.path.exists(p("train_median"))       else None,
    }

    cal_path = p("asset_calibrators")
    if os.path.exists(cal_path):
        pack["calibrators"] = joblib.load(cal_path)
    else:
        pack["calibrators"] = None

    seq_path = p("sequence_model")
    if os.path.exists(seq_path):
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        embed_dim = 32 if symbol == "Universal" else 16
        seq_model = SequenceModel(input_dim=5, embed_dim=embed_dim).to(device)
        seq_model.load_state_dict(torch.load(seq_path, map_location=device))
        seq_model.eval()
        pack["seq_model"] = seq_model
        pack["device"]    = device
    else:
        pack["seq_model"] = None
        pack["device"]    = None

    return pack


def predict_on_test(pack, test_df, symbol=None):
    """Run ensemble prediction on test set (with optional Platt calibration)."""
    feature_cols = pack["feature_cols"]
    le           = pack["le"]
    clf          = pack["clf"]
    second_clf   = pack["second_clf"]
    metadata     = pack["metadata"]
    clip_low     = pack["clip_low"]
    clip_high    = pack["clip_high"]
    train_median = pack["train_median"]
    calibrators  = pack.get("calibrators")

    X_test = test_df[feature_cols].copy()

    # Clipping
    if clip_low is not None and clip_high is not None and train_median is not None:
        X_test = X_test.clip(lower=clip_low, upper=clip_high, axis=1)
        X_test = X_test.replace([np.inf, -np.inf], np.nan).fillna(train_median)

    if second_clf is not None and metadata is not None:
        xgb_w     = metadata.get("xgb_weight", 0.5)
        lgbm_w    = metadata.get("second_model_weight", 0.5)
        conf_thr  = metadata.get("confidence_threshold", 0.0)
        probs     = xgb_w * clf.predict_proba(X_test) + lgbm_w * second_clf.predict_proba(X_test)
        
        # Apply Platt calibration if symbol is provided
        if symbol is not None and calibrators is not None and symbol in calibrators:
            asset_cal = calibrators[symbol]
            if asset_cal is not None:
                probs = asset_cal.predict_proba(probs)
                
        raw       = probs.argmax(axis=1)
        conf      = probs.max(axis=1)
        hold_id   = list(le.classes_).index("HOLD")
        y_pred    = raw.copy()
        y_pred[conf < conf_thr] = hold_id
    else:
        y_pred = clf.predict(X_test)

    return y_pred


def evaluate_single_asset(symbol, ticker, vix_df):
    """Evaluate Universal model + per-asset Platt scaling calibrator on the asset's test split."""
    print(f"\n{'='*60}")
    print(f"  Evaluating: {symbol}  ({ticker}) using Universal model")
    print(f"{'='*60}")

    try:
        pack = load_model_pack("Universal")
    except FileNotFoundError as e:
        print(f"  [SKIP] {e}")
        return None

    # Download data
    df = yf.download(ticker, period=PERIOD, interval="1d", progress=False)
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    df.dropna(inplace=True)

    feat_df = build_features(df, vix_df, ticker_symbol=ticker)

    # Compute labels using train-split quantiles (no leakage)
    metadata = pack["metadata"]
    buy_q    = metadata.get("buy_quantile", 0.70) if metadata else 0.70
    sell_q   = metadata.get("sell_quantile", 0.30) if metadata else 0.30

    split_idx     = int(len(feat_df) * 0.80)
    train_returns = feat_df["fwd_return_5d"].iloc[:split_idx]
    buy_thr       = train_returns.quantile(buy_q)
    sell_thr      = train_returns.quantile(sell_q)

    feat_df["label"] = "HOLD"
    feat_df.loc[feat_df["fwd_return_5d"] >= buy_thr,  "label"] = "BUY"
    feat_df.loc[feat_df["fwd_return_5d"] <= sell_thr, "label"] = "SELL"

    # Sequence embeddings if available
    seq_model = pack.get("seq_model")
    if seq_model is not None:
        feat_df["open"]   = df["open"]
        feat_df["high"]   = df["high"]
        feat_df["low"]    = df["low"]
        feat_df["close"]  = df["close"]
        feat_df["volume"] = df["volume"]

        X_seq, _, valid_dates = create_sequence_dataset(feat_df, seq_len=30, target_col="fwd_return_5d")
        feat_df = feat_df.loc[valid_dates].copy()
        feat_df["sequence"] = list(X_seq)
        feat_df.drop(columns=["open", "high", "low", "close", "volume"], inplace=True)

        split_idx = int(len(feat_df) * 0.80)
        test_df   = feat_df.iloc[split_idx:].copy()

        X_test_seq = np.array(test_df["sequence"].tolist(), dtype=np.float32)
        with torch.no_grad():
            embs = seq_model(torch.tensor(X_test_seq).to(pack["device"])).cpu().numpy()

        embed_dim = pack["metadata"].get("seq_embed_dim", 32) if pack.get("metadata") else 32
        emb_cols = [f"seq_emb_{i}" for i in range(embed_dim)]
        emb_df   = pd.DataFrame(embs, columns=emb_cols, index=test_df.index)
        test_df  = pd.concat([test_df, emb_df], axis=1)
    else:
        split_idx = int(len(feat_df) * 0.80)
        test_df   = feat_df.iloc[split_idx:].copy()

    le     = pack["le"]
    y_true = le.transform(test_df["label"])
    y_pred = predict_on_test(pack, test_df, symbol=symbol)

    acc    = accuracy_score(y_true, y_pred)
    macro  = f1_score(y_true, y_pred, average="macro")
    report = classification_report(y_true, y_pred, target_names=le.classes_, output_dict=True)
    buy_f1  = report.get("BUY",  {}).get("f1-score", 0.0)
    hold_f1 = report.get("HOLD", {}).get("f1-score", 0.0)
    sell_f1 = report.get("SELL", {}).get("f1-score", 0.0)

    print(classification_report(y_true, y_pred, target_names=le.classes_))
    print(f"  Test Accuracy : {acc*100:.1f}%  |  Macro F1: {macro:.2f}")
    print(f"  BUY F1={buy_f1:.2f}  HOLD F1={hold_f1:.2f}  SELL F1={sell_f1:.2f}")

    return {
        "symbol":   symbol,
        "accuracy": round(acc * 100, 1),
        "macro_f1": round(macro, 2),
        "buy_f1":   round(buy_f1, 2),
        "hold_f1":  round(hold_f1, 2),
        "sell_f1":  round(sell_f1, 2),
    }


def evaluate_universal(vix_df):
    """Evaluate Universal model across all supported assets."""
    print(f"\n{'='*60}")
    print(f"  Evaluating: Universal  (multi-asset pool)")
    print(f"{'='*60}")

    try:
        pack = load_model_pack("Universal")
    except FileNotFoundError as e:
        print(f"  [SKIP] {e}")
        return None

    all_true, all_pred = [], []

    for asset_name, ticker in UNIVERSAL_ASSETS.items():
        try:
            df = yf.download(ticker, period=PERIOD, interval="1d", progress=False)
            df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
            df.dropna(inplace=True)
            if len(df) < 100:
                continue
        except Exception as e:
            print(f"  [SKIP] {ticker}: {e}")
            continue

        feat_df = build_features(df, vix_df, ticker_symbol=ticker)

        metadata = pack["metadata"]
        buy_q    = metadata.get("buy_quantile", 0.70) if metadata else 0.70
        sell_q   = metadata.get("sell_quantile", 0.30) if metadata else 0.30

        split_idx     = int(len(feat_df) * 0.80)
        train_returns = feat_df["fwd_return_5d"].iloc[:split_idx]
        buy_thr       = train_returns.quantile(buy_q)
        sell_thr      = train_returns.quantile(sell_q)

        feat_df["label"] = "HOLD"
        feat_df.loc[feat_df["fwd_return_5d"] >= buy_thr,  "label"] = "BUY"
        feat_df.loc[feat_df["fwd_return_5d"] <= sell_thr, "label"] = "SELL"

        seq_model = pack.get("seq_model")
        if seq_model is not None:
            feat_df["open"]   = df["open"]
            feat_df["high"]   = df["high"]
            feat_df["low"]    = df["low"]
            feat_df["close"]  = df["close"]
            feat_df["volume"] = df["volume"]

            X_seq, _, valid_dates = create_sequence_dataset(feat_df, seq_len=30, target_col="fwd_return_5d")
            feat_df = feat_df.loc[valid_dates].copy()
            feat_df["sequence"] = list(X_seq)
            feat_df.drop(columns=["open", "high", "low", "close", "volume"], inplace=True)

            split_idx = int(len(feat_df) * 0.80)
            test_df   = feat_df.iloc[split_idx:].copy()

            X_test_seq = np.array(test_df["sequence"].tolist(), dtype=np.float32)
            with torch.no_grad():
                embs = seq_model(torch.tensor(X_test_seq).to(pack["device"])).cpu().numpy()

            embed_dim = pack["metadata"].get("seq_embed_dim", 32) if pack.get("metadata") else 32
            emb_cols = [f"seq_emb_{i}" for i in range(embed_dim)]
            emb_df   = pd.DataFrame(embs, columns=emb_cols, index=test_df.index)
            test_df  = pd.concat([test_df, emb_df], axis=1)
        else:
            split_idx = int(len(feat_df) * 0.80)
            test_df   = feat_df.iloc[split_idx:].copy()

        # Align features
        le           = pack["le"]
        feature_cols = pack["feature_cols"]
        available    = [c for c in feature_cols if c in test_df.columns]
        if len(available) < len(feature_cols) * 0.8:
            print(f"  [SKIP] {ticker}: too many missing features")
            continue

        y_true = le.transform(test_df["label"])
        y_pred = predict_on_test(pack, test_df, symbol=asset_name)

        all_true.extend(y_true)
        all_pred.extend(y_pred)
        print(f"  {asset_name:<16s} ({ticker}) — test samples: {len(y_true)}")

    if not all_true:
        print("  No data available for Universal evaluation.")
        return None

    le     = pack["le"]
    y_true = np.array(all_true)
    y_pred = np.array(all_pred)

    acc    = accuracy_score(y_true, y_pred)
    macro  = f1_score(y_true, y_pred, average="macro")
    report = classification_report(y_true, y_pred, target_names=le.classes_, output_dict=True)
    buy_f1  = report.get("BUY",  {}).get("f1-score", 0.0)
    hold_f1 = report.get("HOLD", {}).get("f1-score", 0.0)
    sell_f1 = report.get("SELL", {}).get("f1-score", 0.0)

    print(f"\n  Combined test pool: {len(y_true)} samples")
    print(classification_report(y_true, y_pred, target_names=le.classes_))
    print(f"  Test Accuracy : {acc*100:.1f}%  |  Macro F1: {macro:.2f}")
    print(f"  BUY F1={buy_f1:.2f}  HOLD F1={hold_f1:.2f}  SELL F1={sell_f1:.2f}")

    return {
        "symbol":   "Universal",
        "accuracy": round(acc * 100, 1),
        "macro_f1": round(macro, 2),
        "buy_f1":   round(buy_f1, 2),
        "hold_f1":  round(hold_f1, 2),
        "sell_f1":  round(sell_f1, 2),
    }


def main():
    print("=" * 70)
    print("GeoTrade AI — Full Model Evaluation")
    print("=" * 70)

    print("\nDownloading VIX data...")
    vix_df = yf.download("^VIX", period=PERIOD, interval="1d", progress=False)
    vix_df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in vix_df.columns]
    vix_df = vix_df[["close"]].rename(columns={"close": "vix"}).dropna()
    print(f"VIX rows: {len(vix_df)}")

    results = []

    for symbol, ticker in INDIVIDUAL_ASSETS.items():
        row = evaluate_single_asset(symbol, ticker, vix_df)
        if row:
            results.append(row)

    row = evaluate_universal(vix_df)
    if row:
        results.append(row)

    # ── Summary Table ─────────────────────────────────────────────────────────
    print("\n\n" + "=" * 70)
    print("EVALUATION SUMMARY TABLE")
    print("=" * 70)

    # Phase 4 targets (Universal-only, with Platt calibration)
    target = {
        "GOLD":      (42.0, 0.33, 0.50, 0.20, 0.30),
        "OIL_BRENT": (38.0, 0.31, 0.40, 0.35, 0.18),
        "SP500":     (48.0, 0.36, 0.30, 0.60, 0.15),
        "BTCUSD":    (40.0, 0.35, 0.28, 0.52, 0.25),
        "INDA":      (38.0, 0.35, 0.42, 0.18, 0.47),
        "Universal": (55.0, 0.52, 0.40, 0.62, 0.44),
    }

    header = (
        f"{'Asset':<12} {'Acc%':>6} {'MacF1':>6} {'BUY F1':>7} "
        f"{'HOLD F1':>8} {'SELL F1':>8} {'vs Phase3':>10}"
    )
    phase3_baseline = {
        "GOLD": 0.26, "OIL_BRENT": 0.26, "SP500": 0.29,
        "BTCUSD": 0.28, "INDA": 0.28, "Universal": 0.44,
    }
    print(header)
    print("-" * len(header))

    for row in results:
        sym  = row["symbol"]
        acc  = row["accuracy"]
        mf1  = row["macro_f1"]
        bf1  = row["buy_f1"]
        hf1  = row["hold_f1"]
        sf1  = row["sell_f1"]

        tgt       = target.get(sym)
        delta_acc = f"({acc - tgt[0]:+.1f}%)" if tgt else ""
        p3        = phase3_baseline.get(sym)
        vs_p3     = f"F1 {mf1 - p3:+.2f}" if p3 is not None else ""

        print(
            f"{sym:<12} {acc:>5.1f}% {mf1:>6.2f}  {bf1:>6.2f}   "
            f"{hf1:>6.2f}   {sf1:>6.2f}  {delta_acc:>8}  {vs_p3}"
        )

    print("\n  Legend: (+) above Phase 4 target, (-) below target")
    print("  Phase 4 targets (Universal + Platt calibration):")
    print("  GOLD=42%  OIL=38%  SP500=48%  BTC=40%  INDA=38%  Universal=55%")
    print("  Phase 3 baseline macro F1: GOLD=0.26  OIL=0.26  SP500=0.29  BTC=0.28  INDA=0.28  Univ=0.44")


if __name__ == "__main__":
    main()
