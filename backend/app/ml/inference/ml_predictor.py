"""
GeoTrade AI — ML Predictor (Phase 4)
=====================================
Phase 4 changes over Phase 3:
  • Always uses Universal model (individual model lookup removed)
  • VIX fetch upgraded to 2-month window — fixes vix_ma_ratio & vix_change_20d
    (previously hardcoded to 0.0)
  • Sequence embedding dimension: 16 → 32 (matches upgraded SequenceModel)
  • Applies per-asset Platt scaling calibrator (loaded from
    Universal_asset_calibrators.pkl) on top of raw ensemble probabilities
  • 8 new Phase 4 features computed at inference time (stoch_rsi, rsi_div,
    cmf_20, drawdown_20d/60d, regime_flag, trend_strength, fwd_return_10d)
"""

import os
import logging
import math
import numpy as np
import pandas as pd
import joblib
import yfinance as yf
from arch import arch_model
from sqlalchemy.orm import Session
import torch

from ...config import settings
from ...repositories.market_repo import MarketRepository
from ...services.risk_service import risk_service
from ..sequence_model import SequenceModel


logger = logging.getLogger("geotrade.ml.inference.ml_predictor")

SEQ_EMBED_DIM = 32   # must match train_ensemble.py SEQ_EMBED_DIM


# ── Feature Engineering Helpers ───────────────────────────────────────────────

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


# ── Predictor ──────────────────────────────────────────────────────────────────

class MLPredictor:

    # Maps display symbols to asset names used in training (for calibrator lookup)
    SYMBOL_TO_ASSET = {
        # ── Original assets ───────────────────────────────────────────
        "SPY":       "SP500",
        "^GSPC":     "SP500",
        "SP500":     "SP500",
        "MCHI":      "CHINA_EQUITY",
        "INDA":      "INDIA_EQUITY",
        "VGK":       "EUROPE_EQUITY",
        "EWJ":       "JAPAN_EQUITY",
        "EWZ":       "BRAZIL_EQUITY",
        "GC=F":      "GOLD",
        "GOLD":      "GOLD",
        "BZ=F":      "OIL_BRENT",
        "OIL_BRENT": "OIL_BRENT",
        "BTC-USD":   "BTCUSD",
        "BTCUSD":    "BTCUSD",
        "EEM":       "EM_EQUITY",
        "GLD":       "GOLD_ETF",
        "TLT":       "BONDS",
        "UUP":       "DOLLAR",
        "QQQ":       "TECH",
        # ── New assets (Phase 1 expansion) ────────────────────────────
        # Indices
        "IWM":       "SP500",       # Russell 2000 → closest to SP500 regime
        "DIA":       "SP500",       # Dow Jones
        # Stocks — Defense
        "LMT":       "EM_EQUITY",   # Lockheed Martin → equity-like
        "RTX":       "EM_EQUITY",   # RTX Corporation
        "BA":        "EM_EQUITY",   # Boeing
        # Stocks — Tech
        "AAPL":      "TECH",
        "NVDA":      "TECH",
        "MSFT":      "TECH",
        # Stocks — Energy
        "XOM":       "OIL_BRENT",   # Exxon → oil-correlated
        # ETFs
        "ITA":       "EM_EQUITY",   # Defense ETF
        "XLE":       "OIL_BRENT",   # Energy ETF
        "XLF":       "SP500",       # Financial ETF
        "GDX":       "GOLD_ETF",    # Gold miners ETF
        # Commodities
        "SI=F":      "GOLD",        # Silver → gold-correlated
        "NG=F":      "OIL_BRENT",   # Natural Gas → energy-correlated
        # Forex
        "EURUSD=X":  "DOLLAR",
        "USDJPY=X":  "DOLLAR",
        "GBPUSD=X":  "DOLLAR",
        "USDCNH=X":  "DOLLAR",
        "AUDUSD=X":  "DOLLAR",
        # Crypto
        "ETH-USD":   "BTCUSD",
        "SOL-USD":   "BTCUSD",
        # Bonds
        "SHY":       "BONDS",
        "HYG":       "BONDS",
        "BND":       "BONDS",
    }

    TICKER_MAP = {
        # ── Original ───────────────────────────────────────────────────
        "GOLD":      "GC=F",
        "GC=F":      "GC=F",
        "OIL_BRENT": "BZ=F",
        "BZ=F":      "BZ=F",
        "SP500":     "^GSPC",
        "^GSPC":     "^GSPC",
        "SPY":       "SPY",
        "BTCUSD":    "BTC-USD",
        "BTC-USD":   "BTC-USD",
        "INDA":      "INDA",
        "EEM":       "EEM",
        "GLD":       "GLD",
        "TLT":       "TLT",
        "UUP":       "UUP",
        "QQQ":       "QQQ",
        # ── New assets (Phase 1 expansion) ───────────────────────────
        "IWM":       "IWM",
        "DIA":       "DIA",
        "LMT":       "LMT",
        "RTX":       "RTX",
        "BA":        "BA",
        "AAPL":      "AAPL",
        "NVDA":      "NVDA",
        "MSFT":      "MSFT",
        "XOM":       "XOM",
        "ITA":       "ITA",
        "XLE":       "XLE",
        "XLF":       "XLF",
        "GDX":       "GDX",
        "SI=F":      "SI=F",
        "NG=F":      "NG=F",
        "EURUSD=X":  "EURUSD=X",
        "USDJPY=X":  "USDJPY=X",
        "GBPUSD=X":  "GBPUSD=X",
        "USDCNH=X":  "CNY=X",
        "AUDUSD=X":  "AUDUSD=X",
        "ETH-USD":   "ETH-USD",
        "SOL-USD":   "SOL-USD",
        "SHY":       "SHY",
        "HYG":       "HYG",
        "BND":       "BND",
    }

    def __init__(self):
        self.models = {}
        self.loaded = False

    def load_models(self):
        """Loads the Universal model pack (and calibrators) on first call."""
        if self.loaded:
            return

        current_dir = os.path.dirname(os.path.abspath(__file__))
        ml_dir      = os.path.dirname(current_dir)
        models_dir  = os.path.join(ml_dir, "saved_models")

        logger.info(f"Loading ML models from {models_dir}...")
        if not os.path.exists(models_dir):
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__)))))
            models_dir = os.path.abspath(
                os.path.join(backend_dir, settings.ML_MODELS_DIR))
            logger.info(f"Retrying from config-based path: {models_dir}...")

        if not os.path.exists(models_dir):
            logger.warning(f"ML models directory {models_dir} does not exist.")
            return

        try:
            # Phase 4: only Universal is loaded
            symbol = "Universal"

            def p(suffix):
                return os.path.join(models_dir, f"{symbol}_{suffix}.pkl")

            required = [
                "signal_classifier", "drift_regressor", "vol_regressor",
                "label_encoder", "feature_cols",
            ]
            for r in required:
                if not os.path.exists(p(r)):
                    logger.warning(f"Missing required file: {symbol}_{r}.pkl")
                    return

            model_pack = {
                "clf":          joblib.load(p("signal_classifier")),
                "drift_reg":    joblib.load(p("drift_regressor")),
                "vol_reg":      joblib.load(p("vol_regressor")),
                "le":           joblib.load(p("label_encoder")),
                "feature_cols": joblib.load(p("feature_cols")),
                "second_clf":   joblib.load(p("second_signal_classifier"))
                                if os.path.exists(p("second_signal_classifier")) else None,
                "metadata":     joblib.load(p("ensemble_metadata"))
                                if os.path.exists(p("ensemble_metadata")) else None,
                "clip_low":     joblib.load(p("clip_low"))
                                if os.path.exists(p("clip_low"))    else None,
                "clip_high":    joblib.load(p("clip_high"))
                                if os.path.exists(p("clip_high"))   else None,
                "train_median": joblib.load(p("train_median"))
                                if os.path.exists(p("train_median")) else None,
                "calibrators":  joblib.load(p("asset_calibrators"))
                                if os.path.exists(p("asset_calibrators")) else {},
            }

            # Load PyTorch sequence model (32-dim, Phase 4 architecture)
            seq_path = p("sequence_model")
            if os.path.exists(seq_path):
                device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                seq_model = SequenceModel(input_dim=5, embed_dim=SEQ_EMBED_DIM).to(device)
                seq_model.load_state_dict(
                    torch.load(seq_path, map_location=device, weights_only=True))
                seq_model.eval()
                model_pack["seq_model"] = seq_model
                model_pack["device"]    = device
                logger.info(f"Loaded {SEQ_EMBED_DIM}-dim sequence model from {seq_path}")
            else:
                model_pack["seq_model"] = None
                model_pack["device"]    = None

            self.models[symbol] = model_pack
            n_cals = len(model_pack.get("calibrators", {}))
            logger.info(
                f"Universal model loaded. Calibrators: {n_cals} assets. "
                f"Features: {len(model_pack['feature_cols'])}"
            )
            self.loaded = True

        except Exception as e:
            logger.error(f"Error loading Universal model: {e}")

    def predict(self, db: Session, market_id: int) -> dict:
        """
        Runs the full Phase 4 inference pipeline for a given market:
          1. Fetch price history (DB or yfinance fallback)
          2. Fetch VIX (2-month window for correct ma_ratio)
          3. Compute all features including 8 new Phase 4 features
          4. Extract 32-dim sequence embedding
          5. Run Universal ensemble (XGBoost + LightGBM)
          6. Apply per-asset Platt calibrator if available
          7. Return signal, confidence, drift, volatility
        """
        self.load_models()

        repo   = MarketRepository(db)
        market = repo.get_by_id(market_id)
        if not market:
            raise ValueError(f"Market with id={market_id} not found")

        symbol = market.symbol

        # ── 1. Price History ────────────────────────────────────────────────
        history = repo.get_history(market_id, limit=300)

        if len(history) < 20:
            yf_ticker = self.TICKER_MAP.get(symbol, symbol)
            logger.info(
                f"DB has only {len(history)} candles for {symbol}. "
                f"Auto-fetching 2y from yfinance ({yf_ticker})..."
            )
            try:
                yf_df = yf.download(yf_ticker, period="2y", interval="1d", progress=False)
                if yf_df.empty or len(yf_df) < 20:
                    raise ValueError(f"yfinance returned insufficient data for {yf_ticker}")
                yf_df.columns = [
                    c[0].lower() if isinstance(c, tuple) else c.lower()
                    for c in yf_df.columns
                ]
                yf_df = yf_df.tail(300)
                candles = [
                    {
                        "open":   float(row["open"]),
                        "high":   float(row["high"]),
                        "low":    float(row["low"]),
                        "close":  float(row["close"]),
                        "volume": float(row.get("volume", 0) or 0),
                    }
                    for _, row in yf_df.iterrows()
                ]
                logger.info(f"yfinance fallback: loaded {len(candles)} candles for {symbol}")
            except Exception as yfe:
                raise ValueError(
                    f"Insufficient DB history ({len(history)}) and yfinance "
                    f"fallback failed for {symbol}: {yfe}"
                )
        else:
            if len(history) < 252:
                logger.warning(
                    f"Only {len(history)} candles in DB for {symbol} "
                    f"(ideal: 300). Long-window features may be imprecise."
                )
            candles = [
                {
                    "open":   h.open,
                    "high":   h.high,
                    "low":    h.low,
                    "close":  h.close,
                    "volume": h.volume or 0.0,
                }
                for h in reversed(history)
            ]

        # Phase 4: always Universal
        model_pack   = self.models.get("Universal")
        if model_pack is None:
            raise ValueError("Universal model not loaded. Run train_ensemble.py first.")

        feature_cols = model_pack["feature_cols"]

        # ── 2. VIX — 2-month window (Phase 4 fix) ──────────────────────────
        vix_now = 15.0
        vix_change_5d  = 0.0
        vix_change_20d = 0.0
        vix_ma_ratio   = 0.0
        try:
            # 2-month fetch gives us 40+ trading days — enough for 20-day rolling mean
            vix_df = yf.download("^VIX", period="2mo", interval="1d", progress=False)
            if not vix_df.empty and len(vix_df) >= 6:
                vix_df.columns = [
                    c[0].lower() if isinstance(c, tuple) else c.lower()
                    for c in vix_df.columns
                ]
                vix_closes = vix_df["close"].dropna()
                vix_now = float(vix_closes.iloc[-1])

                if len(vix_closes) >= 6:
                    vix_change_5d = float(
                        (vix_closes.iloc[-1] - vix_closes.iloc[-6]) / vix_closes.iloc[-6]
                    )
                if len(vix_closes) >= 21:
                    vix_change_20d = float(
                        (vix_closes.iloc[-1] - vix_closes.iloc[-21]) / vix_closes.iloc[-21]
                    )
                    vix_ma_ratio = float(
                        vix_closes.iloc[-1] / vix_closes.rolling(20).mean().iloc[-1] - 1
                    )
        except Exception as e:
            logger.warning(f"VIX fetch failed: {e}. Using defaults.")

        # ── 3. Feature Engineering ──────────────────────────────────────────
        df        = pd.DataFrame(candles)
        close     = df["close"]
        high      = df["high"]
        low       = df["low"]
        daily_ret = close.pct_change()
        volume    = df["volume"].replace(0, np.nan) if "volume" in df.columns else pd.Series(1.0, index=df.index)

        feat = {}

        # Returns
        feat["return_1d"]  = float(close.pct_change(1).iloc[-1])
        feat["return_2d"]  = float(close.pct_change(2).iloc[-1])
        feat["return_5d"]  = float(close.pct_change(5).iloc[-1])
        feat["return_10d"] = float(close.pct_change(10).iloc[-1])
        feat["return_20d"] = float(close.pct_change(20).iloc[-1])
        feat["return_60d"] = float(
            close.pct_change(min(60, len(close) - 1)).iloc[-1]
        )

        # Volatility / ATR
        n_std = lambda w: min(len(daily_ret), w)
        feat["vol_5d"]  = float((daily_ret.rolling(n_std(5)).std()  * math.sqrt(252)).iloc[-1])
        feat["vol_20d"] = float((daily_ret.rolling(n_std(20)).std() * math.sqrt(252)).iloc[-1])
        feat["vol_60d"] = float((daily_ret.rolling(n_std(60)).std() * math.sqrt(252)).iloc[-1])
        atr_14 = compute_atr(df, min(len(df), 14)) / close
        feat["atr_14"] = float(atr_14.iloc[-1])

        # Momentum
        rsi14 = compute_rsi(close, min(len(close), 14))
        feat["rsi_14"]        = float(rsi14.iloc[-1])
        feat["macd_hist"]     = float(compute_macd(close).iloc[-1])
        feat["bollinger_pct"] = float(compute_bollinger_pct(close, min(len(close), 20)).iloc[-1])

        # Moving-average ratios
        n = lambda w: min(len(close), w)
        sma20  = close.rolling(n(20)).mean()
        sma50  = close.rolling(n(50)).mean()
        sma100 = close.rolling(n(100)).mean()
        sma200 = close.rolling(n(200)).mean()
        ema20  = close.ewm(span=20, adjust=False).mean()
        ema50  = close.ewm(span=50, adjust=False).mean()

        feat["sma_20_ratio"]  = float((close / sma20  - 1).iloc[-1])
        feat["sma_50_ratio"]  = float((close / sma50  - 1).iloc[-1])
        feat["sma_100_ratio"] = float((close / sma100 - 1).iloc[-1])
        feat["sma_200_ratio"] = float((close / sma200 - 1).iloc[-1])
        feat["ema_20_ratio"]  = float((close / ema20  - 1).iloc[-1])
        feat["ema_50_ratio"]  = float((close / ema50  - 1).iloc[-1])

        feat["trend_20_50"]      = float((sma20  / sma50   - 1).iloc[-1])
        feat["trend_50_100"]     = float((sma50  / sma100  - 1).iloc[-1])
        feat["trend_50_200"]     = float((sma50  / sma200  - 1).iloc[-1])
        feat["trend_100_200"]    = float((sma100 / sma200  - 1).iloc[-1])
        feat["ema_sma_20_ratio"] = float((ema20  / sma20   - 1).iloc[-1])
        feat["ema_sma_50_ratio"] = float((ema50  / sma50   - 1).iloc[-1])

        feat["dist_52w_high"] = float((close / close.rolling(n(252)).max() - 1).iloc[-1])
        feat["dist_52w_low"]  = float((close / close.rolling(n(252)).min() - 1).iloc[-1])
        feat["range_20d"]     = float(
            ((high.rolling(n(20)).max() - low.rolling(n(20)).min()) / close).iloc[-1]
        )
        feat["range_60d"]     = float(
            ((high.rolling(n(60)).max() - low.rolling(n(60)).min()) / close).iloc[-1]
        )

        feat["ret_5_20_ratio"]   = float(feat["return_5d"]  / (abs(feat["return_20d"]) + 1e-6))
        feat["ret_20_60_ratio"]  = float(feat["return_20d"] / (abs(feat["return_60d"]) + 1e-6))
        feat["vol_5_20_ratio"]   = float(feat["vol_5d"]  / (feat["vol_20d"] + 1e-6))
        feat["vol_20_60_ratio"]  = float(feat["vol_20d"] / (feat["vol_60d"] + 1e-6))
        feat["atr_vol_ratio"]    = float(feat["atr_14"]  / (feat["vol_20d"] + 1e-6))
        feat["risk_adj_ret_20d"] = float(feat["return_20d"] / (feat["vol_20d"] + 1e-6))
        feat["risk_adj_ret_60d"] = float(feat["return_60d"] / (feat["vol_60d"] + 1e-6))

        # Volume
        vol_r20 = volume / volume.rolling(n(20)).mean()
        vol_r60 = volume / volume.rolling(n(60)).mean()
        vol_z20 = (volume - volume.rolling(n(20)).mean()) / volume.rolling(n(20)).std()
        feat["volume_ratio_20"] = float(vol_r20.fillna(1.0).iloc[-1])
        feat["volume_ratio_60"] = float(vol_r60.fillna(1.0).iloc[-1])
        feat["volume_z_20"]     = float(vol_z20.fillna(0.0).iloc[-1])

        # VIX features (Phase 4 fix — all properly computed now)
        feat["vix"]            = vix_now
        feat["vix_change_5d"]  = vix_change_5d
        feat["vix_change_20d"] = vix_change_20d
        feat["vix_ma_ratio"]   = vix_ma_ratio
        feat["vix_vol_ratio"]  = float(vix_now / 100.0 / (feat["vol_20d"] + 1e-6))

        # GARCH(1,1) conditional volatility
        try:
            ret_s = daily_ret.fillna(0.0)
            if ret_s.std() > 0.0001:
                gm = arch_model(ret_s * 100.0, vol="Garch", p=1, q=1, dist="Normal")
                gr = gm.fit(disp="off", show_warning=False)
                feat["garch_sigma_1d"] = float(gr.conditional_volatility.iloc[-1] / 100.0)
            else:
                feat["garch_sigma_1d"] = float(feat["vol_20d"] / math.sqrt(252.0))
        except Exception:
            feat["garch_sigma_1d"] = float(feat["vol_20d"] / math.sqrt(252.0))

        # Phase 4: 8 new SELL-friendly features

        # 1. Stochastic RSI
        rsi_min  = rsi14.rolling(n(14)).min()
        rsi_max  = rsi14.rolling(n(14)).max()
        stoch_k  = (rsi14 - rsi_min) / (rsi_max - rsi_min + 1e-6)
        feat["stoch_rsi"] = float(stoch_k.rolling(3).mean().iloc[-1])

        # 2. RSI Divergence
        feat["rsi_div"] = float((rsi14 - rsi14.rolling(n(10)).mean()).iloc[-1])

        # 3. Chaikin Money Flow
        mf_vol = ((close - low) - (high - close)) / (high - low + 1e-6) * volume
        cmf = mf_vol.rolling(n(20)).sum() / volume.rolling(n(20)).sum()
        feat["cmf_20"] = float(cmf.fillna(0.0).iloc[-1])

        # 4. Drawdown from rolling high
        feat["drawdown_20d"] = float((close / close.rolling(n(20)).max() - 1).iloc[-1])
        feat["drawdown_60d"] = float((close / close.rolling(n(60)).max() - 1).iloc[-1])

        # 5. Regime flag
        feat["regime_flag"] = float((vix_now > 20) and (feat["vol_20d"] > 0.20))

        # 6. Trend strength
        feat["trend_strength"] = abs(feat["sma_20_ratio"]) + abs(feat["sma_50_ratio"])

        # 7. Multi-horizon context (no forward look at inference — use recent 10-day return as proxy)
        feat["fwd_return_10d"] = float(close.pct_change(10).iloc[-1])

        # Asset dummies (Universal asset categories)
        current_asset = self.SYMBOL_TO_ASSET.get(symbol, "SP500")
        all_asset_cats = list(set(self.SYMBOL_TO_ASSET.values()))
        for asset_key in all_asset_cats:
            feat[f"asset_{asset_key}"] = 1.0 if current_asset == asset_key else 0.0

        # ── 4. Sequence Embedding (32-dim) ──────────────────────────────────
        seq_model = model_pack.get("seq_model")
        if seq_model is not None:
            try:
                seq_candles = candles[-30:]
                if len(seq_candles) == 30:
                    ref_price  = seq_candles[0]["close"] or 1.0
                    norm_open  = [c["open"]   / ref_price - 1.0 for c in seq_candles]
                    norm_high  = [c["high"]   / ref_price - 1.0 for c in seq_candles]
                    norm_low   = [c["low"]    / ref_price - 1.0 for c in seq_candles]
                    norm_close = [c["close"]  / ref_price - 1.0 for c in seq_candles]
                    mean_vol   = np.mean([c["volume"] for c in seq_candles])
                    norm_vol   = [c["volume"] / (mean_vol + 1e-6) for c in seq_candles]

                    seq_arr   = np.column_stack(
                        [norm_open, norm_high, norm_low, norm_close, norm_vol]
                    ).astype(np.float32)
                    seq_input = np.expand_dims(seq_arr, axis=0)  # (1, 30, 5)

                    device = model_pack["device"]
                    with torch.no_grad():
                        emb = seq_model(
                            torch.tensor(seq_input).to(device)
                        ).cpu().numpy()[0]

                    for i in range(SEQ_EMBED_DIM):      # 32 dims (was 16)
                        feat[f"seq_emb_{i}"] = float(emb[i])
            except Exception as e:
                logger.error(f"Sequence embedding failed for {symbol}: {e}")

        # ── 5. Align features with trained model's feature order ─────────────
        row = {col: feat.get(col, 0.0) for col in feature_cols}
        for col in feature_cols:
            if col not in feat:
                logger.warning(f"Feature '{col}' missing — defaulting to 0.0")
        input_df = pd.DataFrame([row])

        # Outlier clipping
        clip_low    = model_pack.get("clip_low")
        clip_high   = model_pack.get("clip_high")
        train_med   = model_pack.get("train_median")
        if clip_low is not None and clip_high is not None and train_med is not None:
            input_df = input_df.clip(lower=clip_low, upper=clip_high, axis=1)
            input_df = input_df.replace([np.inf, -np.inf], np.nan).fillna(train_med)

        # ── 6. Ensemble Prediction ──────────────────────────────────────────
        clf        = model_pack["clf"]
        second_clf = model_pack.get("second_clf")
        metadata   = model_pack.get("metadata")
        drift_reg  = model_pack["drift_reg"]
        vol_reg    = model_pack["vol_reg"]
        le         = model_pack["le"]

        if second_clf is not None and metadata is not None:
            xgb_w    = metadata.get("xgb_weight", 0.5)
            lgbm_w   = metadata.get("second_model_weight", 0.5)
            conf_thr = metadata.get("confidence_threshold", 0.35)
            raw_proba = (
                xgb_w  * clf.predict_proba(input_df)[0] +
                lgbm_w * second_clf.predict_proba(input_df)[0]
            )
        else:
            raw_proba = clf.predict_proba(input_df)[0]
            conf_thr  = 0.35

        # ── 7. Per-Asset Platt Calibration (Phase 4) ─────────────────────────
        calibrators   = model_pack.get("calibrators", {})
        asset_cal     = calibrators.get(current_asset)
        proba         = raw_proba.copy()

        if asset_cal is not None:
            try:
                proba = asset_cal.predict_proba(raw_proba.reshape(1, -1))[0]
                logger.debug(
                    f"[{symbol}] Platt calibrator applied for {current_asset}: "
                    f"raw={raw_proba.round(3)} -> cal={proba.round(3)}"
                )
            except Exception as e:
                logger.warning(f"[{symbol}] Platt calibration failed: {e}. Using raw probs.")

        signal_id  = int(proba.argmax())
        confidence = float(proba[signal_id])

        if confidence < conf_thr:
            predicted_signal = "HOLD"
        else:
            predicted_signal = str(le.classes_[signal_id])

        # Regression predictions
        predicted_drift      = float(drift_reg.predict(input_df)[0])
        predicted_volatility = float(vol_reg.predict(input_df)[0])

        return {
            "predicted_signal":    predicted_signal,
            "confidence":          confidence,
            "predicted_drift":     predicted_drift,
            "predicted_volatility": predicted_volatility,
            "garch_sigma_1d":      float(feat.get("garch_sigma_1d", 0.02)),
            "vix":                 float(feat.get("vix", 15.0)),
            "source":              "ml-ensemble-universal-phase4",
        }


ml_predictor = MLPredictor()
