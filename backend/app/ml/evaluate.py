import os
import math
import warnings
import numpy as np
import pandas as pd
import yfinance as yf
import joblib
from sklearn.metrics import classification_report, mean_absolute_error, r2_score
from arch import arch_model
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

warnings.filterwarnings('ignore')


# ── Config ────────────────────────────────────────────────────────────────
PERIOD = '5y'
SIGNAL_THRESH = 0.02
HORIZON = 5
SAVE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'saved_models'))

ASSETS = {
    'GOLD':      'GC=F',
    'OIL_BRENT': 'BZ=F',
    'SP500':     '^GSPC',
    'BTCUSD':    'BTC-USD',
    'INDA':      'INDA',
}

# ── Technical Indicators ──────────────────────────────────────────────────
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
    signal_line= macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line - signal_line

def compute_bollinger_pct(series, period=20):
    ma  = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    return (series - lower) / (upper - lower).replace(0, np.nan)

def compute_atr(df, period=14):
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low']  - df['close'].shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def safe_div(a, b):
    return a / b.replace(0, np.nan)

# ── Feature Builder ───────────────────────────────────────────────────────
def build_features(df, vix_df, symbol):
    f = pd.DataFrame(index=df.index)
    close = df['close']
    high = df['high']
    low = df['low']
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
        ret_series = df['close'].pct_change().fillna(0.0)
        if ret_series.std() > 0.0001:
            garch_model_fit = arch_model(ret_series * 100.0, vol="Garch", p=1, q=1, dist="Normal")
            garch_res = garch_model_fit.fit(disp="off", show_warning=False)
            f["garch_sigma_1d"] = garch_res.conditional_volatility / 100.0
        else:
            f["garch_sigma_1d"] = f["vol_20d"] / math.sqrt(252.0)
    except Exception:
        f["garch_sigma_1d"] = f["vol_20d"] / math.sqrt(252.0)

    # Asset dummies
    SYMBOL_TO_ASSET = {
        "SPY": "SP500",
        "^GSPC": "SP500",
        "SP500": "SP500",
        "MCHI": "CHINA_EQUITY",
        "INDA": "INDIA_EQUITY",
        "VGK": "EUROPE_EQUITY",
        "EWJ": "JAPAN_EQUITY",
        "EWZ": "BRAZIL_EQUITY",
        "GC=F": "GOLD",
        "GOLD": "GOLD",
        "BZ=F": "OIL_BRENT",
        "OIL_BRENT": "OIL_BRENT",
        "BTC-USD": "BTCUSD",
        "BTCUSD": "BTCUSD",
    }
    current_asset = SYMBOL_TO_ASSET.get(symbol, "SP500")
    for asset_key in SYMBOL_TO_ASSET.values():
        col_name = f"asset_{asset_key}"
        f[col_name] = 1.0 if current_asset == asset_key else 0.0

    # Target & labels
    f['fwd_return_5d'] = df['close'].pct_change(HORIZON).shift(-HORIZON)
    
    f['label'] = 'HOLD'
    f.loc[f['fwd_return_5d'] > SIGNAL_THRESH, 'label'] = 'BUY'
    f.loc[f['fwd_return_5d'] < -SIGNAL_THRESH, 'label'] = 'SELL'
    
    f.dropna(inplace=True)
    return f


# ── Evaluation ────────────────────────────────────────────────────────────
def evaluate_model(symbol):
    print(f"\n==========================================")
    print(f"Evaluating Saved Models for: {symbol}")
    print(f"==========================================")
    
    # Paths to the saved files
    clf_path = os.path.join(SAVE_DIR, f'{symbol}_signal_classifier.pkl')
    drift_path = os.path.join(SAVE_DIR, f'{symbol}_drift_regressor.pkl')
    vol_path = os.path.join(SAVE_DIR, f'{symbol}_vol_regressor.pkl')
    le_path = os.path.join(SAVE_DIR, f'{symbol}_label_encoder.pkl')
    feat_path = os.path.join(SAVE_DIR, f'{symbol}_feature_cols.pkl')
    
    if not (os.path.exists(clf_path) and os.path.exists(drift_path) and os.path.exists(vol_path)):
        print(f"Error: Missing trained model file(s) in {SAVE_DIR}.")
        return
        
    # Load model binaries
    clf = joblib.load(clf_path)
    drift_reg = joblib.load(drift_path)
    vol_reg = joblib.load(vol_path)
    le = joblib.load(le_path)
    feature_cols = joblib.load(feat_path)
    
    # Load optional ensemble components
    second_clf_path = os.path.join(SAVE_DIR, f'{symbol}_second_signal_classifier.pkl')
    meta_path = os.path.join(SAVE_DIR, f'{symbol}_ensemble_metadata.pkl')
    second_clf = joblib.load(second_clf_path) if os.path.exists(second_clf_path) else None
    metadata = joblib.load(meta_path) if os.path.exists(meta_path) else None
    
    # Determine ticker & GTI flag
    if symbol == 'Universal':
        # Use SPY as proxy for universal evaluation
        ticker = 'SPY'
        include_gti = False
    else:
        ticker = ASSETS.get(symbol)
        include_gti = True
        
    if not ticker:
        print(f"Error: Symbol {symbol} not recognized in assets dictionary.")
        return
        
    # Fetch VIX & historical close data
    print(f"Fetching VIX and {ticker} data from Yahoo Finance...")
    vix = yf.download('^VIX', period=PERIOD, interval='1d', progress=False)
    vix.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in vix.columns]
    vix = vix[['close']].rename(columns={'close': 'vix'}).dropna()
    
    df = yf.download(ticker, period=PERIOD, interval='1d', progress=False)
    df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
    df.dropna(inplace=True)
    
    # Process features
    feature_df = build_features(df, vix, symbol=ticker)
    
    # Re-apply dynamic quantile thresholds strictly calculated on the 80% train split
    buy_q = 0.70
    sell_q = 0.30
    if metadata is not None:
        buy_q = metadata.get("buy_quantile", 0.70)
        sell_q = metadata.get("sell_quantile", 0.30)
        
    split_idx = int(len(feature_df) * 0.80)
    train_returns = feature_df['fwd_return_5d'].iloc[:split_idx]
    buy_threshold = train_returns.quantile(buy_q)
    sell_threshold = train_returns.quantile(sell_q)
    
    feature_df['label'] = 'HOLD'
    feature_df.loc[feature_df['fwd_return_5d'] >= buy_threshold, 'label'] = 'BUY'
    feature_df.loc[feature_df['fwd_return_5d'] <= sell_threshold, 'label'] = 'SELL'
    
    # Process sequences if sequence model exists
    seq_model_path = os.path.join(SAVE_DIR, f'{symbol}_sequence_model.pkl')
    has_seq = os.path.exists(seq_model_path)
    if has_seq:
        import torch
        from app.ml.sequence_model import create_sequence_dataset, SequenceModel
        # Add raw columns temporarily for sequence normalization
        feature_df["open"] = df["open"]
        feature_df["high"] = df["high"]
        feature_df["low"] = df["low"]
        feature_df["close"] = df["close"]
        feature_df["volume"] = df["volume"]
        
        X_seq, _, valid_dates = create_sequence_dataset(feature_df, seq_len=30, target_col="fwd_return_5d")
        feature_df = feature_df.loc[valid_dates].copy()
        feature_df["sequence"] = list(X_seq)
        feature_df.drop(columns=["open", "high", "low", "close", "volume"], inplace=True)
        
    # Create the time-series split (evaluating only on the 20% unseen test data)
    split = int(len(feature_df) * 0.80)
    test_df = feature_df.iloc[split:].copy()
    
    if has_seq:
        X_test_seq = np.array(test_df["sequence"].tolist(), dtype=np.float32)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        state_dict = torch.load(seq_model_path, map_location=device)
        
        # Dynamically determine the embedding dimension from fc2 bias parameter
        embed_dim = state_dict["fc2.bias"].shape[0] if "fc2.bias" in state_dict else 16
        
        seq_model = SequenceModel(input_dim=5, embed_dim=embed_dim).to(device)
        seq_model.load_state_dict(state_dict)
        seq_model.eval()
        
        with torch.no_grad():
            test_embeddings = seq_model(torch.tensor(X_test_seq).to(device)).cpu().numpy()
            
        emb_cols = [f"seq_emb_{i}" for i in range(embed_dim)]
        test_emb_df = pd.DataFrame(test_embeddings, columns=emb_cols, index=test_df.index)
        test_df = pd.concat([test_df, test_emb_df], axis=1)
        
    X_test = test_df[feature_cols]

    y_test_cls = le.transform(test_df['label'])
    y_test_drift = test_df['fwd_return_5d'] * (252/5)
    y_test_vol = test_df['vol_20d']
    
    # --- 1. Evaluate Classifier ---
    print("\n--- 1. Classifier Evaluation ---")
    if second_clf is not None and metadata is not None:
        xgb_w = metadata.get("xgb_weight", 0.5)
        lgbm_w = metadata.get("second_model_weight", 0.5)
        conf_thr = metadata.get("confidence_threshold", 0.0)
        
        xgb_probs = clf.predict_proba(X_test)
        lgbm_probs = second_clf.predict_proba(X_test)
        probs = xgb_w * xgb_probs + lgbm_w * lgbm_probs
        
        raw_preds = probs.argmax(axis=1)
        confidences = probs.max(axis=1)
        
        hold_id = list(le.classes_).index("HOLD")
        y_pred_cls = raw_preds.copy()
        y_pred_cls[confidences < conf_thr] = hold_id
    else:
        y_pred_cls = clf.predict(X_test)
        
    print(classification_report(y_test_cls, y_pred_cls, target_names=le.classes_))
    
    # --- 2. Evaluate Regressors ---
    print("--- 2. Regressor Evaluation ---")
    drift_preds = drift_reg.predict(X_test)
    print(f"Drift Regressor (Expected Return) Error:")
    print(f"  Mean Absolute Error (MAE) : {mean_absolute_error(y_test_drift, drift_preds):.4f} ({mean_absolute_error(y_test_drift, drift_preds)*100:.2f}% annualized)")
    print(f"  R-squared (R2 Score)      : {r2_score(y_test_drift, drift_preds):.4f}")
    
    vol_preds = vol_reg.predict(X_test)
    print(f"\nVolatility Regressor Error:")
    print(f"  Mean Absolute Error (MAE) : {mean_absolute_error(y_test_vol, vol_preds):.4f} ({mean_absolute_error(y_test_vol, vol_preds)*100:.2f}% annualized)")
    print(f"  R-squared (R2 Score)      : {r2_score(y_test_vol, vol_preds):.4f}")

def main():
    import sys
    symbol = 'GOLD'
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.lower() == 'universal':
            symbol = 'Universal'
        else:
            symbol = arg.upper()
        
    evaluate_model(symbol)

if __name__ == '__main__':
    main()
