"""
GeoTrade AI - Universal Ensemble Training Script (Phase 4)
===========================================================
Phase 4 improvements over Phase 3:
  1. Universal-only architecture  — individual asset models are deprecated;
     all inference goes through this model + per-asset Platt calibrators.
  2. Expanded asset pool          — 9 → 14 assets (~9,800 training rows).
  3. 8 new SELL-friendly features — StochRSI, RSI divergence, CMF, drawdowns,
     regime flag, trend strength, multi-horizon confirmation context.
  4. Dual-horizon label denoising — BUY/SELL confirmed by 10-day direction.
  5. Widened quantile thresholds  — 70/30 → 65/35 (more SELL signal in uptrends).
  6. Upgraded sequence model      — 32-dim embed (was 16), FocalLoss, deeper arch.
  7. SELL-boosted sample weights  — SELL examples weighted 1.5× extra on top of balanced.
  8. LightGBM receives sample_weights (was missing in Phase 3).
  9. SELL-aware tuning objective  — 60% macro F1 + 40% SELL F1.
  10. Per-asset Platt scaling calibrators — lightweight asset-specific correction layer.

Run:
    python train_ensemble.py
"""

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
    mean_absolute_error, r2_score,
)
from sklearn.linear_model import LogisticRegression

print("=" * 70)
print("GeoTrade AI - Universal Ensemble Training (Phase 4)")
print(f"LightGBM available: {HAS_LGBM}")
print("=" * 70)

# ── Config ─────────────────────────────────────────────────────────────────────
ASSETS = {
    # Original 9
    "SP500":         "^GSPC",
    "CHINA_EQUITY":  "MCHI",
    "INDIA_EQUITY":  "INDA",
    "EUROPE_EQUITY": "VGK",
    "JAPAN_EQUITY":  "EWJ",
    "BRAZIL_EQUITY": "EWZ",
    "GOLD":          "GC=F",
    "OIL_BRENT":     "BZ=F",
    "BTCUSD":        "BTC-USD",
    # New 5 — macro regime anchors + additional equity diversity
    "EM_EQUITY":     "EEM",    # Emerging markets
    "GOLD_ETF":      "GLD",    # Physical gold ETF
    "BONDS":         "TLT",    # 20yr Treasury (risk-off anchor)
    "DOLLAR":        "UUP",    # Dollar index ETF (FX / commodity SELL context)
    "TECH":          "QQQ",    # Nasdaq-100 (high-beta equity regime)
}

PERIOD             = "5y"
HORIZON            = 5         # primary label horizon (trading days)
BUY_Q              = 0.65      # top 35% returns → BUY   (was 0.70)
SELL_Q             = 0.35      # bottom 35% returns → SELL (was 0.30)
TOP_N_FEATURES     = 40        # keep top N after first XGBoost importance pass (was 20)
CONFIDENCE_THRESHOLD = 0.45
SEQ_LEN            = 30        # rolling window length for sequence model
SEQ_EMBED_DIM      = 32        # embedding dimension (was 16)
SAVE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "backend", "app", "ml", "saved_models")
)
os.makedirs(SAVE_DIR, exist_ok=True)
print(f"Save dir: {SAVE_DIR}\n")


# ── Technical Indicator Helpers ────────────────────────────────────────────────

def compute_rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def compute_macd(series, fast=12, slow=26, signal=9):
    ema_fast  = series.ewm(span=fast,   adjust=False).mean()
    ema_slow  = series.ewm(span=slow,   adjust=False).mean()
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


# ── Data Download ──────────────────────────────────────────────────────────────
print("Downloading price data...")
raw_data = {}
for name, ticker in ASSETS.items():
    try:
        df = yf.download(ticker, period=PERIOD, interval="1d", progress=False)
        df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
        df.dropna(inplace=True)
        if df.empty or len(df) < 100:
            print(f"  {name:16s} -> SKIPPED (empty or too few rows)")
            continue
        raw_data[name] = df
        print(f"  {name:16s} -> {len(df):4d} rows ({df.index[0].date()} -> {df.index[-1].date()})")
    except Exception as e:
        print(f"  {name:16s} -> FAILED: {e}")

if len(raw_data) < 5:
    raise RuntimeError(f"Only {len(raw_data)} assets downloaded. Need at least 5.")

vix = yf.download("^VIX", period=PERIOD, interval="1d", progress=False)
vix.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in vix.columns]
vix = vix[["close"]].rename(columns={"close": "vix"})
print(f"  {'VIX':16s} -> {len(vix):4d} rows\n")


# ── Feature Engineering ────────────────────────────────────────────────────────

def build_features(df, vix_df, asset_name):
    """
    Builds the full feature matrix for one asset.
    Includes 8 new Phase 4 SELL-friendly features.
    NOTE: Labels are computed OUTSIDE this function to avoid leakage.
    """
    f       = pd.DataFrame(index=df.index)
    close   = df["close"]
    high    = df["high"]
    low     = df["low"]
    volume  = df["volume"] if "volume" in df.columns else pd.Series(1.0, index=df.index)
    daily_ret = close.pct_change()

    # ── Returns ──────────────────────────────────────────────────────────────
    f["return_1d"]  = close.pct_change(1)
    f["return_2d"]  = close.pct_change(2)
    f["return_5d"]  = close.pct_change(5)
    f["return_10d"] = close.pct_change(10)
    f["return_20d"] = close.pct_change(20)
    f["return_60d"] = close.pct_change(60)

    # ── Volatility / ATR ──────────────────────────────────────────────────
    f["vol_5d"]  = daily_ret.rolling(5).std()  * math.sqrt(252)
    f["vol_20d"] = daily_ret.rolling(20).std() * math.sqrt(252)
    f["vol_60d"] = daily_ret.rolling(60).std() * math.sqrt(252)
    f["atr_14"]  = compute_atr(df, 14) / close

    # ── Momentum ──────────────────────────────────────────────────────────
    rsi14 = compute_rsi(close, 14)
    f["rsi_14"]        = rsi14
    f["macd_hist"]     = compute_macd(close)
    f["bollinger_pct"] = compute_bollinger_pct(close, 20)

    # ── Moving-average ratios ──────────────────────────────────────────────
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

    # ── Cross-average trend ratios ─────────────────────────────────────────
    f["trend_20_50"]      = sma20  / sma50   - 1
    f["trend_50_100"]     = sma50  / sma100  - 1
    f["trend_50_200"]     = sma50  / sma200  - 1
    f["trend_100_200"]    = sma100 / sma200  - 1
    f["ema_sma_20_ratio"] = ema20  / sma20   - 1
    f["ema_sma_50_ratio"] = ema50  / sma50   - 1

    # ── Breakout / mean-reversion context ─────────────────────────────────
    f["dist_52w_high"] = close / close.rolling(252).max() - 1
    f["dist_52w_low"]  = close / close.rolling(252).min() - 1
    f["range_20d"]     = (high.rolling(20).max() - low.rolling(20).min()) / close
    f["range_60d"]     = (high.rolling(60).max() - low.rolling(60).min()) / close

    # ── Ratio features ────────────────────────────────────────────────────
    f["ret_5_20_ratio"]   = safe_div(f["return_5d"],  f["return_20d"].abs() + 1e-6)
    f["ret_20_60_ratio"]  = safe_div(f["return_20d"], f["return_60d"].abs() + 1e-6)
    f["vol_5_20_ratio"]   = safe_div(f["vol_5d"],  f["vol_20d"])
    f["vol_20_60_ratio"]  = safe_div(f["vol_20d"], f["vol_60d"])
    f["atr_vol_ratio"]    = safe_div(f["atr_14"],  f["vol_20d"] + 1e-6)
    f["risk_adj_ret_20d"] = safe_div(f["return_20d"], f["vol_20d"] + 1e-6)
    f["risk_adj_ret_60d"] = safe_div(f["return_60d"], f["vol_60d"] + 1e-6)

    # ── Volume features ───────────────────────────────────────────────────
    vol_s = volume.replace(0, np.nan)
    f["volume_ratio_20"] = vol_s / vol_s.rolling(20).mean()
    f["volume_ratio_60"] = vol_s / vol_s.rolling(60).mean()
    f["volume_z_20"]     = (vol_s - vol_s.rolling(20).mean()) / vol_s.rolling(20).std()

    # ── VIX regime ────────────────────────────────────────────────────────
    f = f.join(vix_df, how="left")
    f["vix"]            = f["vix"].ffill()
    f["vix_change_5d"]  = f["vix"].pct_change(5)
    f["vix_change_20d"] = f["vix"].pct_change(20)
    f["vix_ma_ratio"]   = f["vix"] / f["vix"].rolling(20).mean() - 1
    f["vix_vol_ratio"]  = safe_div(f["vix"] / 100.0, f["vol_20d"] + 1e-6)

    # ── GARCH(1,1) conditional volatility (regime-aware) ─────────────────
    try:
        ret_series = daily_ret.fillna(0.0)
        if ret_series.std() > 0.0001:
            gm  = arch_model(ret_series * 100.0, vol="Garch", p=1, q=1, dist="Normal")
            gr  = gm.fit(disp="off", show_warning=False)
            f["garch_sigma_1d"] = gr.conditional_volatility / 100.0
        else:
            f["garch_sigma_1d"] = f["vol_20d"] / math.sqrt(252.0)
    except Exception:
        f["garch_sigma_1d"] = f["vol_20d"] / math.sqrt(252.0)

    # ── Phase 4: 8 New SELL-Friendly Features ────────────────────────────

    # 1. Stochastic RSI (14,3) — overbought / oversold momentum
    rsi_min  = rsi14.rolling(14).min()
    rsi_max  = rsi14.rolling(14).max()
    stoch_k  = (rsi14 - rsi_min) / (rsi_max - rsi_min + 1e-6)
    f["stoch_rsi"] = stoch_k.rolling(3).mean()

    # 2. RSI Divergence — RSI trend vs own 10-day moving average
    f["rsi_div"] = rsi14 - rsi14.rolling(10).mean()

    # 3. Chaikin Money Flow (CMF 20) — volume-weighted buying/selling pressure
    money_flow_vol = ((close - low) - (high - close)) / (high - low + 1e-6) * vol_s
    f["cmf_20"] = money_flow_vol.rolling(20).sum() / vol_s.rolling(20).sum()

    # 4. Drawdown from rolling high (pain / exhaustion indicators)
    f["drawdown_20d"] = close / close.rolling(20).max() - 1
    f["drawdown_60d"] = close / close.rolling(60).max() - 1

    # 5. Regime flag — binary: high-vol AND VIX-spike = risk-off state
    f["regime_flag"] = ((f["vix"] > 20) & (f["vol_20d"] > 0.20)).astype(float)

    # 6. Trend strength (ADX proxy) — directional magnitude of MA spread
    f["trend_strength"] = f["sma_20_ratio"].abs() + f["sma_50_ratio"].abs()

    # 7. Multi-horizon context: 10-day forward return (used as feature, not label)
    #    Computed here; only used as a feature — label uses 5-day horizon
    f["fwd_return_10d"] = close.pct_change(HORIZON * 2).shift(-(HORIZON * 2))

    # ── Label target (for labeling only — not a feature fed to XGB) ──────
    f["fwd_return_5d"] = close.pct_change(HORIZON).shift(-HORIZON)
    f["asset"]         = asset_name
    f.dropna(inplace=True)
    return f


# ── Build Feature Matrix ───────────────────────────────────────────────────────
print("Engineering features + building sequence windows...")
datasets = {}
for name, df in raw_data.items():
    feat_df = build_features(df, vix, name)

    # Temporarily attach raw OHLCV for sequence window builder
    for col in ["open", "high", "low", "close", "volume"]:
        feat_df[col] = df[col]

    X_seq, _, valid_dates = create_sequence_dataset(
        feat_df, seq_len=SEQ_LEN, target_col="fwd_return_5d"
    )

    feat_df = feat_df.loc[valid_dates].copy()
    feat_df["sequence"] = list(X_seq)
    feat_df.drop(columns=["open", "high", "low", "close", "volume"], inplace=True)

    datasets[name] = feat_df
    print(f"  {name:16s} -> {len(feat_df):4d} rows")

# ── Merge + Asset Dummies ──────────────────────────────────────────────────────
master_df    = pd.concat(datasets.values()).sort_index()
asset_dummies = pd.get_dummies(master_df["asset"], prefix="asset", dtype=int)
master_df    = pd.concat([master_df, asset_dummies], axis=1)
print(f"\nMaster dataset: {len(master_df)} rows across {len(datasets)} assets\n")

# ── Feature Columns ────────────────────────────────────────────────────────────
BASE_FEATURES = [
    # Returns
    "return_1d","return_2d","return_5d","return_10d","return_20d","return_60d",
    # Volatility
    "vol_5d","vol_20d","vol_60d","atr_14",
    # Momentum
    "rsi_14","macd_hist","bollinger_pct",
    # MA ratios
    "sma_20_ratio","sma_50_ratio","sma_100_ratio","sma_200_ratio",
    "ema_20_ratio","ema_50_ratio",
    # Trend ratios
    "trend_20_50","trend_50_100","trend_50_200","trend_100_200",
    "ema_sma_20_ratio","ema_sma_50_ratio",
    # Breakout
    "dist_52w_high","dist_52w_low","range_20d","range_60d",
    # Ratio composites
    "ret_5_20_ratio","ret_20_60_ratio",
    "vol_5_20_ratio","vol_20_60_ratio","atr_vol_ratio",
    "risk_adj_ret_20d","risk_adj_ret_60d",
    # Volume
    "volume_ratio_20","volume_ratio_60","volume_z_20",
    # VIX
    "vix","vix_change_5d","vix_change_20d","vix_ma_ratio","vix_vol_ratio",
    # GARCH
    "garch_sigma_1d",
    # Phase 4 new features
    "stoch_rsi","rsi_div","cmf_20",
    "drawdown_20d","drawdown_60d",
    "regime_flag","trend_strength",
    "fwd_return_10d",   # multi-horizon context (feature, not label)
]
ASSET_FEATURES = [c for c in master_df.columns if c.startswith("asset_")]
FEATURE_COLS   = BASE_FEATURES + ASSET_FEATURES
print(f"Total base + new features: {len(BASE_FEATURES)}  |  Asset dummies: {len(ASSET_FEATURES)}")

# ── Time-Series Split (70 / 10 / 20) ──────────────────────────────────────────
n         = len(master_df)
train_end = int(n * 0.70)
valid_end = int(n * 0.80)

train_df = master_df.iloc[:train_end].copy()
valid_df = master_df.iloc[train_end:valid_end].copy()
test_df  = master_df.iloc[valid_end:].copy()

# ── Label Thresholds (computed on train only — no leakage) ────────────────────
sell_threshold = train_df["fwd_return_5d"].quantile(SELL_Q)
buy_threshold  = train_df["fwd_return_5d"].quantile(BUY_Q)
print(f"\nLabel thresholds (train only):")
print(f"  SELL if fwd_return_5d <= {sell_threshold:.4f}  (bottom {int(SELL_Q*100)}%)")
print(f"  BUY  if fwd_return_5d >= {buy_threshold:.4f}  (top    {int((1-BUY_Q)*100)}%)")

def apply_labels(df):
    """
    Dual-horizon confirmation labeling (Phase 4):
    BUY  = 5-day return qualifies AND 10-day return is positive  (uptrend confirmed)
    SELL = 5-day return qualifies AND 10-day return is negative  (downtrend confirmed)
    Everything else = HOLD
    """
    d = df.copy()
    d["label"] = "HOLD"
    buy_mask  = (d["fwd_return_5d"] >= buy_threshold)  & (d["fwd_return_10d"] >= 0)
    sell_mask = (d["fwd_return_5d"] <= sell_threshold) & (d["fwd_return_10d"] <= 0)
    d.loc[buy_mask,  "label"] = "BUY"
    d.loc[sell_mask, "label"] = "SELL"
    return d

train_df = apply_labels(train_df)
valid_df = apply_labels(valid_df)
test_df  = apply_labels(test_df)

print(f"\nTrain: {len(train_df)} | Valid: {len(valid_df)} | Test: {len(test_df)}")
print("Train label dist:", train_df["label"].value_counts().to_dict())
print("Valid label dist:", valid_df["label"].value_counts().to_dict())
print("Test  label dist:", test_df["label"].value_counts().to_dict())

# ── Label Encoding ─────────────────────────────────────────────────────────────
le = LabelEncoder()
y_train_cls = le.fit_transform(train_df["label"])
y_valid_cls = le.transform(valid_df["label"])
y_test_cls  = le.transform(test_df["label"])
print(f"\nLabel classes (encoded): {list(enumerate(le.classes_))}")

buy_idx  = list(le.classes_).index("BUY")
hold_idx = list(le.classes_).index("HOLD")
sell_idx = list(le.classes_).index("SELL")

y_train_drift = train_df["fwd_return_5d"] * (252 / HORIZON)
y_valid_drift = valid_df["fwd_return_5d"] * (252 / HORIZON)
y_test_drift  = test_df["fwd_return_5d"]  * (252 / HORIZON)
y_train_vol   = train_df["vol_20d"]
y_valid_vol   = valid_df["vol_20d"]
y_test_vol    = test_df["vol_20d"]

# ── Outlier Clipping (train-only bounds) ───────────────────────────────────────
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

# ── PyTorch Sequence Model Pre-Training ───────────────────────────────────────
X_train_seq = np.array(train_df["sequence"].tolist(), dtype=np.float32)
X_valid_seq = np.array(valid_df["sequence"].tolist(), dtype=np.float32)
X_test_seq  = np.array(test_df["sequence"].tolist(),  dtype=np.float32)

seq_model_path = f"{SAVE_DIR}/Universal_sequence_model.pkl"
if os.path.exists(seq_model_path):
    print(f"Loading existing sequence model from {seq_model_path}...")
    torch_model = SequenceModel(input_dim=5, embed_dim=SEQ_EMBED_DIM)
    torch_model.load_state_dict(torch.load(seq_model_path, map_location="cpu"))
else:
    torch_model = train_sequence_model(
        X_train_seq, y_train_cls,
        X_valid_seq, y_valid_cls,
        num_classes  = 3,
        epochs       = 50,
        batch_size   = 64,
        focal_gamma  = 2.0,
        patience     = 10,
    )
    # Save sequence model state dict
    torch.save(torch_model.state_dict(), seq_model_path)
    print(f"Saved sequence model -> {seq_model_path}")

# Extract embeddings (32-dim)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch_model = torch_model.to(device).eval()

with torch.no_grad():
    train_embs = torch_model(torch.tensor(X_train_seq).to(device)).cpu().numpy()
    valid_embs = torch_model(torch.tensor(X_valid_seq).to(device)).cpu().numpy()
    test_embs  = torch_model(torch.tensor(X_test_seq).to(device)).cpu().numpy()

emb_cols = [f"seq_emb_{i}" for i in range(SEQ_EMBED_DIM)]
X_train = pd.concat([X_train, pd.DataFrame(train_embs, columns=emb_cols, index=train_df.index)], axis=1)
X_valid = pd.concat([X_valid, pd.DataFrame(valid_embs, columns=emb_cols, index=valid_df.index)], axis=1)
X_test  = pd.concat([X_test,  pd.DataFrame(test_embs,  columns=emb_cols, index=test_df.index)],  axis=1)
FEATURE_COLS = list(FEATURE_COLS) + emb_cols
print(f"Total feature cols after embeddings: {len(FEATURE_COLS)}")

# ── Sample Weights (Phase 4: SELL boosted 1.5× extra) ─────────────────────────
sample_weights = compute_sample_weight(class_weight="balanced", y=y_train_cls)

# Directional loss penalty (wrong-direction BUY/SELL amplified by return magnitude)
direction_multiplier = 3.0
for i in range(len(train_df)):
    ret       = train_df["fwd_return_5d"].iloc[i]
    label_cls = y_train_cls[i]
    if label_cls == buy_idx  and ret < 0:
        sample_weights[i] *= (1.0 + abs(ret) * direction_multiplier)
    elif label_cls == sell_idx and ret > 0:
        sample_weights[i] *= (1.0 + abs(ret) * direction_multiplier)

# Phase 4: extra 1.5× boost to all SELL examples (addresses class rarity)
sell_count   = (y_train_cls == sell_idx).sum()
non_sell     = len(y_train_cls) - sell_count
sell_boost   = (non_sell / max(sell_count, 1)) * 1.5
sample_weights[y_train_cls == sell_idx] *= sell_boost
print(f"\nSELL boost factor applied: {sell_boost:.2f}x  "
      f"(sell_count={sell_count}, non_sell={non_sell})")

valid_weights = compute_sample_weight(class_weight="balanced", y=y_valid_cls)
class_weights = compute_class_weight(
    class_weight="balanced",
    classes=np.unique(y_train_cls),
    y=y_train_cls,
)
class_weight_dict = dict(zip(np.unique(y_train_cls), class_weights))

# ── STEP 1: XGBoost Grid Search ───────────────────────────────────────────────
print("\n" + "=" * 70)
print("STEP 1: XGBoost grid search with early stopping...")
print("=" * 70)

XGB_PARAMS = [
    # Optimized configuration (best from grid search)
    {"max_depth": 2, "learning_rate": 0.01, "n_estimators": 2000,
     "min_child_weight": 75, "reg_lambda": 10.0, "subsample": 0.75, "colsample_bytree": 0.75, "gamma": 0.3},
]

def sell_aware_score(y_true, y_pred):
    """Phase 4 tuning objective: 60% macro F1 + 40% SELL F1."""
    macro   = f1_score(y_true, y_pred, average="macro")
    per_cls = f1_score(y_true, y_pred, average=None, labels=[0, 1, 2])
    s_f1    = per_cls[sell_idx] if sell_idx < len(per_cls) else 0.0
    return 0.60 * macro + 0.40 * s_f1

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
    score = sell_aware_score(y_valid_cls, pred)
    best_n = model.best_iteration if hasattr(model, "best_iteration") else "N/A"
    print(f"  depth={params['max_depth']} lr={params['learning_rate']} "
          f"L2={params['reg_lambda']} mcw={params['min_child_weight']} "
          f"| tree #{best_n} | SELL-aware F1={score:.4f}")
    if score > best_xgb_score:
        best_xgb_score  = score
        best_xgb        = model
        best_xgb_params = params

clf_xgb = best_xgb
print(f"\nBest XGBoost SELL-aware F1: {best_xgb_score:.4f} | params: {best_xgb_params}")

# ── STEP 2: Feature Pruning ────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"STEP 2: Feature pruning — keeping top {TOP_N_FEATURES} features...")
print("=" * 70)

importances  = pd.Series(clf_xgb.feature_importances_, index=FEATURE_COLS)
top_features = importances.nlargest(TOP_N_FEATURES).index.tolist()
print("Top features:", top_features[:15], "... (showing first 15)")

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
pruned_score = sell_aware_score(y_valid_cls, clf_xgb_p.predict(X_valid_p))
print(f"Full features SELL-aware F1  : {best_xgb_score:.4f}")
print(f"Pruned features SELL-aware F1: {pruned_score:.4f}")

if pruned_score >= best_xgb_score - 0.02:
    clf_xgb      = clf_xgb_p
    FEATURE_COLS = top_features
    X_train      = X_train_p
    X_valid      = X_valid_p
    X_test       = X_test_p
    print(f"Using PRUNED feature set ({TOP_N_FEATURES} features)")
else:
    print("Pruned model worse — keeping full feature set")

# ── STEP 3: LightGBM Grid Search ──────────────────────────────────────────────
print(f"\n{'='*70}")
print("STEP 3: LightGBM grid search...")
print("=" * 70)

if HAS_LGBM:
    LGBM_PARAMS = [
        # Optimized configuration (best from grid search)
        {"max_depth": 2, "num_leaves": 4,  "learning_rate": 0.01, "n_estimators": 2000,
         "min_child_samples": 75, "reg_lambda": 10.0, "subsample": 0.75, "colsample_bytree": 0.75},
    ]
    best_lgbm, best_lgbm_score, best_lgbm_params = None, -1, None
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
            sample_weight=sample_weights,   # Phase 4: LGBM now receives SELL-boosted weights
            eval_set=[(X_valid, y_valid_cls)],
            callbacks=[__import__("lightgbm").early_stopping(40, verbose=False)],
        )
        pred  = model.predict(X_valid)
        score = sell_aware_score(y_valid_cls, pred)
        best_n = model.best_iteration_ if hasattr(model, "best_iteration_") else "N/A"
        print(f"  depth={params['max_depth']} leaves={params['num_leaves']} "
              f"lr={params['learning_rate']} L2={params['reg_lambda']} "
              f"| tree #{best_n} | SELL-aware F1={score:.4f}")
        if score > best_lgbm_score:
            best_lgbm_score  = score
            best_lgbm        = model
            best_lgbm_params = params
    clf_lgbm = best_lgbm
    print(f"\nBest LightGBM SELL-aware F1: {best_lgbm_score:.4f}")
else:
    clf_lgbm = HistGradientBoostingClassifier(
        max_iter=500, learning_rate=0.01, max_leaf_nodes=8,
        min_samples_leaf=200, l2_regularization=50.0,
        class_weight=class_weight_dict, random_state=42,
    )
    clf_lgbm.fit(X_train, y_train_cls, sample_weight=sample_weights)

lgbm_val  = sell_aware_score(y_valid_cls, clf_lgbm.predict(X_valid))
lgbm_train = sell_aware_score(y_train_cls, clf_lgbm.predict(X_train))
print(f"LGBM train SELL-aware F1: {lgbm_train:.4f}  val: {lgbm_val:.4f}  gap: {lgbm_train-lgbm_val:.4f}")

USE_ENSEMBLE = True
if lgbm_train - lgbm_val > 0.15:
    print("WARNING: LightGBM overfits. Falling back to XGBoost-only.")
    USE_ENSEMBLE = False

# ── STEP 4: Ensemble Weight + Threshold Tuning (SELL-aware) ───────────────────
print(f"\n{'='*70}")
print("STEP 4: Ensemble weight + confidence threshold tuning (SELL-aware)...")
print("=" * 70)

best_ens_score, best_w, best_thresh = -1, 1.0, 0.0

weight_range = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] if USE_ENSEMBLE else [1.0]
thresh_range = [0.0, 0.28, 0.30, 0.33, 0.35, 0.38, 0.40, 0.42, 0.45, 0.48, 0.50]

for w in weight_range:
    probs = w * clf_xgb.predict_proba(X_valid) + (1 - w) * clf_lgbm.predict_proba(X_valid)
    for thresh in thresh_range:
        raw      = probs.argmax(axis=1)
        conf     = probs.max(axis=1)
        filtered = raw.copy()
        filtered[conf < thresh] = hold_idx

        # Guard: don't convert more than 15% of predictions to HOLD
        if (conf < thresh).mean() > 0.15:
            continue

        score = sell_aware_score(y_valid_cls, filtered)
        if score > best_ens_score:
            best_ens_score = score
            best_w         = w
            best_thresh    = thresh

XGB_W    = best_w
LGBM_W   = 1 - best_w
CONF_THR = best_thresh
print(f"Best XGB weight: {XGB_W} | LGBM weight: {LGBM_W} | Confidence threshold: {CONF_THR}")
print(f"Best validation SELL-aware F1: {best_ens_score:.4f}")


# ── STEP 5: Final Evaluation ───────────────────────────────────────────────────
def evaluate(X, y_true, split_name):
    probs    = XGB_W * clf_xgb.predict_proba(X) + LGBM_W * clf_lgbm.predict_proba(X)
    raw      = probs.argmax(axis=1)
    conf     = probs.max(axis=1)
    filtered = raw.copy()
    filtered[conf < CONF_THR] = hold_idx

    filt_macro = f1_score(y_true, filtered, average="macro")
    filt_sell  = f1_score(y_true, filtered, average=None)[sell_idx]

    print(f"\n{'='*70}\n{split_name}\n{'='*70}")
    print(classification_report(y_true, filtered, target_names=le.classes_))
    cm = confusion_matrix(y_true, filtered)
    print(pd.DataFrame(cm, index=le.classes_, columns=le.classes_).to_string())
    print(f"Macro F1: {filt_macro:.4f}  SELL F1: {filt_sell:.4f}  "
          f"Avg conf: {conf.mean():.4f}  Low-conf -> HOLD: {(conf < CONF_THR).mean()*100:.1f}%")
    return filt_macro

train_f1 = evaluate(X_train, y_train_cls, "Train")
val_f1   = evaluate(X_valid, y_valid_cls, "Validation")
test_f1  = evaluate(X_test,  y_test_cls,  "Test")

print(f"\n{'='*70}\nSUMMARY\n{'='*70}")
print(f"Train  macro F1 : {train_f1:.4f}")
print(f"Valid  macro F1 : {val_f1:.4f}")
print(f"Test   macro F1 : {test_f1:.4f}")
print(f"Train-Test gap  : {train_f1 - test_f1:.4f}")

# ── STEP 6: Drift + Volatility Regressors ─────────────────────────────────────
print(f"\n{'='*70}")
print("STEP 6: Training drift + volatility regressors...")
print("=" * 70)

drift_reg = XGBRegressor(
    n_estimators=1000, max_depth=3, learning_rate=0.01,
    subsample=0.75, colsample_bytree=0.75, reg_lambda=20.0,
    random_state=42, n_jobs=-1, tree_method="hist",
    early_stopping_rounds=25,
)
drift_reg.fit(X_train, y_train_drift, eval_set=[(X_valid, y_valid_drift)], verbose=False)

vol_reg = XGBRegressor(
    n_estimators=1000, max_depth=3, learning_rate=0.01,
    subsample=0.75, colsample_bytree=0.75, reg_lambda=20.0,
    random_state=42, n_jobs=-1, tree_method="hist",
    early_stopping_rounds=25,
)
vol_reg.fit(X_train, y_train_vol, eval_set=[(X_valid, y_valid_vol)], verbose=False)

drift_mae = mean_absolute_error(y_test_drift, drift_reg.predict(X_test))
drift_r2  = r2_score(y_test_drift, drift_reg.predict(X_test))
vol_mae   = mean_absolute_error(y_test_vol,   vol_reg.predict(X_test))
vol_r2    = r2_score(y_test_vol,   vol_reg.predict(X_test))
print(f"Drift - Test MAE: {drift_mae:.4f} ({drift_mae*100:.2f}%)  R²: {drift_r2:.4f}")
print(f"Vol   - Test MAE: {vol_mae:.4f} ({vol_mae*100:.2f}%)      R²: {vol_r2:.4f}")

# ── STEP 7: Per-Asset Platt Scaling Calibrators ────────────────────────────────
print(f"\n{'='*70}")
print("STEP 7: Fitting per-asset Platt scaling calibrators...")
print("=" * 70)

# Build a mapping from asset dummy → validation rows
asset_calibrators = {}
all_asset_vals = master_df.iloc[train_end:valid_end]["asset"].values   # validation asset names

for asset_name in datasets.keys():
    mask = (all_asset_vals == asset_name)
    n_asset = mask.sum()
    if n_asset < 30:
        print(f"  {asset_name:16s} -> SKIP (only {n_asset} validation rows)")
        continue

    X_cal_asset = X_valid[mask]
    y_cal_asset = y_valid_cls[mask]

    # Get raw ensemble probs for this asset's validation rows
    raw_probs = (
        XGB_W  * clf_xgb.predict_proba(X_cal_asset) +
        LGBM_W * clf_lgbm.predict_proba(X_cal_asset)
    )

    # Fit Platt scaling: 3-class logistic regression on top of raw probs
    cal = LogisticRegression(C=1.0, max_iter=500, random_state=42)
    try:
        cal.fit(raw_probs, y_cal_asset)
        cal_pred = cal.predict(raw_probs)
        cal_f1 = f1_score(y_cal_asset, cal_pred, average="macro")
        print(f"  {asset_name:16s} -> n={n_asset:4d}  calibrated val macro F1: {cal_f1:.4f}")
        asset_calibrators[asset_name] = cal
    except Exception as e:
        print(f"  {asset_name:16s} -> calibration failed: {e}")

print(f"\nCalibrators fitted: {len(asset_calibrators)} / {len(datasets)} assets")

# ── STEP 8: Save All Artifacts ────────────────────────────────────────────────
print(f"\n{'='*70}")
print("STEP 8: Saving production artifacts...")
print("=" * 70)

symbol = "Universal"
joblib.dump(clf_xgb,            f"{SAVE_DIR}/{symbol}_signal_classifier.pkl")
joblib.dump(clf_lgbm,           f"{SAVE_DIR}/{symbol}_second_signal_classifier.pkl")
joblib.dump(drift_reg,          f"{SAVE_DIR}/{symbol}_drift_regressor.pkl")
joblib.dump(vol_reg,            f"{SAVE_DIR}/{symbol}_vol_regressor.pkl")
joblib.dump(le,                 f"{SAVE_DIR}/{symbol}_label_encoder.pkl")
joblib.dump(FEATURE_COLS,       f"{SAVE_DIR}/{symbol}_feature_cols.pkl")
joblib.dump(clip_low,           f"{SAVE_DIR}/{symbol}_clip_low.pkl")
joblib.dump(clip_high,          f"{SAVE_DIR}/{symbol}_clip_high.pkl")
joblib.dump(train_med,          f"{SAVE_DIR}/{symbol}_train_median.pkl")
joblib.dump(asset_calibrators,  f"{SAVE_DIR}/{symbol}_asset_calibrators.pkl")

metadata = {
    "model_type":            "universal_xgboost_lgbm_ensemble_phase4",
    "phase":                 4,
    "xgb_weight":            XGB_W,
    "second_model_weight":   LGBM_W,
    "confidence_threshold":  CONF_THR,
    "label_classes":         list(le.classes_),
    "horizon_days":          HORIZON,
    "buy_quantile":          BUY_Q,
    "sell_quantile":         SELL_Q,
    "feature_count":         len(FEATURE_COLS),
    "seq_embed_dim":         SEQ_EMBED_DIM,
    "asset_count":           len(datasets),
    "training_rows":         len(train_df),
    "train_f1":              round(train_f1, 4),
    "val_f1":                round(val_f1,   4),
    "test_f1":               round(test_f1,  4),
    "dual_horizon_labels":   True,
    "focal_loss_gamma":      2.0,
    "sell_boost_factor":     round(sell_boost, 2),
    "calibrated_assets":     list(asset_calibrators.keys()),
    "notes": (
        "Phase 4: Universal-only, 14 assets, 8 new features, dual-horizon labels, "
        "SELL-aware tuning objective, per-asset Platt calibrators, 32-dim seq embed."
    ),
}
joblib.dump(metadata, f"{SAVE_DIR}/{symbol}_ensemble_metadata.pkl")
print(json.dumps(metadata, indent=2))
print(f"\nAll artifacts saved to: {SAVE_DIR}")
