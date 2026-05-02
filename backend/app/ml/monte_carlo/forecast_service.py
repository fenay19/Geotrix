"""
Monte Carlo Forecast Service
==============================
The master orchestrator for Stage 3 of the GeoTrade intelligence pipeline.

Flow:
    1. Fetches current price + history from DB.
    2. Computes historical volatility from OHLC data (used as Stage 2 placeholder
       until the XGBoost ML model is trained; replaced by ML drift/volatility
       once Stage 2 is implemented).
    3. Runs the GBM Monte Carlo engine (10,000 paths).
    4. Computes all risk metrics (VaR, CVaR, Sharpe, P(loss)).
    5. Returns a fully structured forecast dict ready for the API response.

Stage 2 integration point:
    When the ML model (Stage 2) is trained, call:
        from ...ml.inference.ml_predictor import ml_predictor
        ml_result = ml_predictor.predict(db, market_id)
        drift      = ml_result["predicted_drift"]
        volatility = ml_result["predicted_volatility"]
    and pass those into run_simulation(). Until then, we derive drift/volatility
    from historical data using the existing VolatilityModel.
"""

import logging
import math
from typing import Optional

from sqlalchemy.orm import Session

from ...repositories.market_repo import MarketRepository
from ...services.risk_service import risk_service
from ...ai.forecasting.volatility_model import volatility_model
from .gbm_engine import gbm_engine
from .risk_metrics import risk_metrics

logger = logging.getLogger("geotrade.ml.monte_carlo.forecast")

# ── Tuneable constants ────────────────────────────────────────────────────────
DEFAULT_N_SIMS:   int   = 10_000   # number of Monte Carlo paths
DEFAULT_HORIZON:  int   = 30       # trading days to simulate
RISK_FREE_RATE:   float = 0.05     # 5% annual risk-free rate (US Treasuries)

# Asset-specific baseline volatility (used as fallback when history is thin)
BASELINE_VOLATILITY: dict = {
    "GOLD":      0.14,
    "OIL_BRENT": 0.28,
    "SP500":     0.18,
    "BTCUSD":    0.65,
    "XAUUSD":    0.14,
}
DEFAULT_VOLATILITY: float = 0.20


class MonteCarloForecastService:
    """
    Orchestrates the full Monte Carlo forecast pipeline for any market asset.

    Currently operates in 'historical mode' (Stage 2 not yet trained):
      - drift     = computed from recent average daily return × 252
      - volatility = computed via VolatilityModel from OHLC history

    Once Stage 2 ML models are available, these inputs will be replaced
    by ml_predictor.predict() outputs automatically.
    """

    def run_forecast(
        self,
        db: Session,
        market_id: int,
        horizon: int = DEFAULT_HORIZON,
        n_sims: int = DEFAULT_N_SIMS,
        # Stage 2 ML injection points (None = auto-derive from history)
        ml_drift: Optional[float] = None,
        ml_volatility: Optional[float] = None,
        ml_signal: Optional[str] = None,
        ml_confidence: Optional[float] = None,
        ml_source: str = "historical-fallback",
    ) -> dict:
        """
        Runs the full Monte Carlo forecast for a given market.

        Args:
            db:            SQLAlchemy session.
            market_id:     ID of the Market row.
            horizon:       Days to simulate forward.
            n_sims:        Number of simulation paths.
            ml_drift:      Drift from Stage 2 ML model (if available).
            ml_volatility: Volatility from Stage 2 ML model (if available).
            ml_signal:     BUY/SELL/HOLD from Stage 2 ML model.
            ml_confidence: Confidence score from Stage 2 ML model.
            ml_source:     Tagged source string ("ml-xgboost" | "llm-backup" | "historical-fallback")

        Returns:
            Full structured forecast dict (see return block below).

        Raises:
            ValueError: If the market is not found or has no price data.
        """
        # ── 1. Fetch market record ────────────────────────────────────────────
        repo   = MarketRepository(db)
        market = repo.get_by_id(market_id)
        if not market:
            raise ValueError(f"Market with id={market_id} not found.")

        S0 = market.price
        if not S0 or S0 <= 0:
            raise ValueError(f"Market {market.symbol} has no valid price (got {S0}).")

        # ── 2. Fetch OHLC history ─────────────────────────────────────────────
        history = repo.get_history(market_id, limit=120)  # last 120 candles to fit GARCH
        candles = [
            {"open": h.open, "high": h.high, "low": h.low, "close": h.close}
            for h in reversed(history)              # oldest → newest
        ]

        # ── 3. Determine drift + volatility ──────────────────────────────────
        # Priority: ML model output > dynamic ML prediction > historical computation > baseline default
        if ml_drift is not None and ml_volatility is not None:
            drift      = ml_drift
            volatility = ml_volatility
            logger.info(
                "[%s] Using ML-provided drift=%.4f, vol=%.4f",
                market.symbol, drift, volatility,
            )
        else:
            try:
                from ...ml.inference.ml_predictor import ml_predictor
                ml_res = ml_predictor.predict(db, market_id)
                drift = ml_res["predicted_drift"]
                volatility = ml_res["predicted_volatility"]
                ml_signal = ml_res["predicted_signal"]
                ml_confidence = ml_res["confidence"]
                ml_source = ml_res["source"]
                logger.info(
                    "[%s] Dynamically loaded ML drift=%.4f, vol=%.4f, signal=%s from %s",
                    market.symbol, drift, volatility, ml_signal, ml_source
                )
            except Exception as e:
                logger.warning("[%s] Dynamic ML prediction failed, falling back to history: %s", market.symbol, e)
                ml_source = "historical-fallback"
                if len(candles) >= 10:
                    drift, volatility = self._derive_from_history(candles, market.symbol)
                else:
                    drift      = 0.0
                    volatility = BASELINE_VOLATILITY.get(market.symbol, DEFAULT_VOLATILITY)
                    logger.warning(
                        "[%s] Insufficient history (%d candles), using baseline vol=%.2f",
                        market.symbol, len(candles), volatility,
                    )

        # ── 4. Get GTI for context ────────────────────────────────────────────
        gti = risk_service.get_latest_gti(db)
        gti_score = gti.current_score if gti else 50.0

        # Apply a simple GTI adjustment to drift when no ML model is present:
        # High geopolitical tension (GTI > 70) shaves 1-2% off expected drift.
        if ml_drift is None and gti_score > 70:
            gti_penalty = -((gti_score - 70) / 100) * 0.02
            drift = round(drift + gti_penalty, 6)
            logger.debug("[%s] GTI penalty applied: %.6f", market.symbol, gti_penalty)

        # ── 5. Run GARCH Monte Carlo simulation ───────────────────────────────
        import pandas as pd
        closes = [c["close"] for c in candles]
        daily_ret = pd.Series(closes).pct_change().dropna()
        
        garch_success = False
        garch_params = {}
        current_var = 0.04
        
        try:
            from arch import arch_model
            ret_series = daily_ret * 100.0  # Scale returns by 100
            if ret_series.std() > 0.0001:
                garch_model_fit = arch_model(ret_series, vol="Garch", p=1, q=1, dist="Normal")
                garch_res = garch_model_fit.fit(disp="off", show_warning=False)
                garch_params = {
                    "mu": float(garch_res.params.get("mu", 0.0)),
                    "omega": float(garch_res.params.get("omega", 0.01)),
                    "alpha": float(garch_res.params.get("alpha[1]", 0.05)),
                    "beta": float(garch_res.params.get("beta[1]", 0.90)),
                }
                current_var = float(garch_res.conditional_volatility.iloc[-1] ** 2)
                garch_success = True
        except Exception as e:
            logger.warning("[%s] GARCH fitting failed for Monte Carlo, falling back to standard GBM: %s", market.symbol, e)

        if garch_success:
            logger.info(
                "[%s] Running GARCH Monte Carlo: S0=%.2f, horizon=%d, n_sims=%d",
                market.symbol, S0, horizon, n_sims,
            )
            price_paths = gbm_engine.run_garch_simulation(
                S0=S0,
                garch_params=garch_params,
                current_var=current_var,
                horizon=horizon,
                n_sims=n_sims,
            )
        else:
            logger.info(
                "[%s] Running standard GBM: S0=%.2f, μ=%.4f, σ=%.4f, horizon=%d, n_sims=%d",
                market.symbol, S0, drift, volatility, horizon, n_sims,
            )
            price_paths = gbm_engine.run_simulation(
                S0=S0,
                drift=drift,
                volatility=volatility,
                horizon=horizon,
                n_sims=n_sims,
            )


        # ── 6. Summarize paths ────────────────────────────────────────────────
        path_summary = gbm_engine.summarize(price_paths)

        # ── 7. Compute risk metrics ───────────────────────────────────────────
        risk_report = risk_metrics.full_report(
            price_paths=price_paths,
            S0=S0,
            horizon=horizon,
            risk_free_rate=RISK_FREE_RATE,
        )

        # ── 8. Determine trend label ──────────────────────────────────────────
        final_median = path_summary["median"][-1]
        if final_median > S0 * 1.01:
            trend = "UP"
        elif final_median < S0 * 0.99:
            trend = "DOWN"
        else:
            trend = "SIDEWAYS"

        # ── 9. Build and return response ──────────────────────────────────────
        return {
            # Identity
            "symbol":         market.symbol,
            "market_id":      market_id,
            "category":       market.category,

            # Inputs
            "current_price":        round(S0, 4),
            "drift_used":           round(drift, 6),
            "volatility_used":      round(volatility, 4),
            "gti_score":            round(gti_score, 1),
            "horizon_days":         horizon,
            "n_simulations":        n_sims,

            # Signal from Stage 2 (or None if no ML yet)
            "signal":               ml_signal,
            "signal_confidence":    ml_confidence,
            "source":               ml_source,

            # Price path outputs
            "forecast":             path_summary["median"],        # 50th pct
            "upper_bound":          path_summary["upper_95"],      # 95th pct
            "lower_bound":          path_summary["lower_05"],      # 5th pct
            "upper_75":             path_summary["upper_75"],      # 75th pct
            "lower_25":             path_summary["lower_25"],      # 25th pct
            "mean_path":            path_summary["mean"],

            # Risk metrics
            "var_95":               risk_report["var_95"],
            "cvar_95":              risk_report["cvar_95"],
            "probability_of_loss":  risk_report["probability_of_loss"],
            "expected_return":      risk_report["expected_return"],
            "sharpe_ratio":         risk_report["sharpe_ratio"],
            "best_case_price":      risk_report["best_case"],
            "worst_case_price":     risk_report["worst_case"],
            "median_final_price":   risk_report["median_final_price"],

            # Summary
            "trend":                trend,
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _derive_from_history(self, candles: list, symbol: str) -> tuple:
        """
        Derives annualized drift and volatility from recent OHLC candles.

        Returns:
            (drift: float, volatility: float)
        """
        vol_result = volatility_model.compute_from_ohlc(candles)
        volatility = vol_result["annualized_vol"]

        # Fallback if volatility came back as 0 (insufficient data)
        if volatility == 0.0:
            volatility = BASELINE_VOLATILITY.get(symbol, DEFAULT_VOLATILITY)

        # Compute annualized drift from average daily return
        closes = [c["close"] for c in candles]
        if len(closes) >= 2:
            daily_returns = [
                (closes[i] - closes[i - 1]) / closes[i - 1]
                for i in range(1, len(closes))
                if closes[i - 1] != 0
            ]
            avg_daily_return = sum(daily_returns) / len(daily_returns)
            drift = avg_daily_return * 252          # annualize
        else:
            drift = 0.0

        logger.debug(
            "[%s] Derived from history: drift=%.4f, vol=%.4f (%d candles)",
            symbol, drift, volatility, len(candles),
        )
        return round(drift, 6), round(volatility, 4)


# Module-level singleton
monte_carlo_forecast_service = MonteCarloForecastService()
