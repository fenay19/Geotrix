from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ...dependencies import get_db
from ...services.market_service import market_service
from ...services.risk_service import risk_service
from ...ai.forecasting.price_forecaster import PriceForecaster
from ...ml.monte_carlo.forecast_service import monte_carlo_forecast_service
from ...config import settings

router = APIRouter()


# ── Existing: Linear / OpenAI Forecast ───────────────────────────────────────

@router.get("/{symbol}")
def get_price_forecast(
    symbol: str,
    horizon_days: int = Query(7, ge=1, le=30, description="Days to forecast"),
    db: Session = Depends(get_db)
):
    """
    Generates an AI-driven price forecast for a specific market asset.
    Uses recent OHLC history and current Global Tension Index (GTI) as context.
    (Linear regression + OpenAI reasoning)
    """
    # 1. Verify market exists
    market = market_service.get_market(db, symbol)
    if not market:
        raise HTTPException(status_code=404, detail=f"Market {symbol} not found")

    # 2. Get recent history (last 30 candles)
    history = market_service.get_market_history(db, symbol, limit=30)
    if not history:
        raise HTTPException(
            status_code=400,
            detail="Not enough historical data to generate forecast"
        )

    # 3. Get current GTI context
    gti = risk_service.get_latest_gti(db)
    gti_score = gti.current_score if gti else 50.0

    # 4. Convert history models to dicts for the forecaster
    candles = [
        {
            "close": h.close,
            "high":  h.high,
            "low":   h.low,
            "open":  h.open,
        }
        for h in reversed(history)   # Forecaster expects oldest → newest
    ]

    # 5. Generate forecast
    forecaster = PriceForecaster(api_key=settings.OPENAI_API_KEY)
    forecast_data = forecaster.forecast(
        symbol=symbol,
        horizon=horizon_days,
        history=candles,
        gti_score=gti_score,
    )

    if not forecast_data:
        raise HTTPException(status_code=500, detail="Failed to generate forecast")

    return forecast_data


# ── NEW: Monte Carlo / GBM Forecast ──────────────────────────────────────────

@router.get("/mc/{market_id}")
def get_monte_carlo_forecast(
    market_id: int,
    horizon: int = Query(30, ge=1, le=90, description="Trading days to simulate"),
    n_sims: int  = Query(10000, ge=1000, le=50000, description="Number of simulation paths"),
    db: Session  = Depends(get_db),
):
    """
    Runs a Geometric Brownian Motion (GBM) Monte Carlo simulation for a market asset.

    - Derives drift and volatility from 60 days of historical OHLC data.
    - Adjusts drift down when Global Tension Index (GTI) is high.
    - Simulates `n_sims` independent price paths over `horizon` trading days.
    - Returns percentile paths (5th, 25th, 50th, 75th, 95th), plus full
      institutional risk metrics: VaR, CVaR, Sharpe Ratio, P(loss).

    When Stage 2 ML model is trained, this endpoint will automatically
    use ML-predicted drift and volatility instead of historical values.
    """
    try:
        result = monte_carlo_forecast_service.run_forecast(
            db=db,
            market_id=market_id,
            horizon=horizon,
            n_sims=n_sims,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")


@router.get("/mc/compare/{symbol}")
def compare_forecasts(
    symbol: str,
    horizon_days: int = Query(30, ge=1, le=90, description="Days to forecast"),
    db: Session = Depends(get_db),
):
    """
    Returns a side-by-side comparison of:
      1. Linear / OpenAI forecast (existing method)
      2. Monte Carlo GBM forecast (new probabilistic method)

    Useful for the frontend to show both forecasts on the same chart,
    demonstrating the difference between a point estimate and a probability cone.
    """
    # ── Linear forecast ───────────────────────────────────────────────────────
    market = market_service.get_market(db, symbol)
    if not market:
        raise HTTPException(status_code=404, detail=f"Market '{symbol}' not found")

    history = market_service.get_market_history(db, symbol, limit=30)
    gti = risk_service.get_latest_gti(db)
    gti_score = gti.current_score if gti else 50.0

    linear_result = None
    if history:
        candles = [
            {"close": h.close, "high": h.high, "low": h.low, "open": h.open}
            for h in reversed(history)
        ]
        forecaster   = PriceForecaster(api_key=settings.OPENAI_API_KEY)
        linear_result = forecaster.forecast(
            symbol=symbol,
            horizon=horizon_days,
            history=candles,
            gti_score=gti_score,
        )

    # ── Monte Carlo forecast ──────────────────────────────────────────────────
    mc_result = None
    try:
        mc_result = monte_carlo_forecast_service.run_forecast(
            db=db,
            market_id=market.id,
            horizon=horizon_days,
        )
    except Exception as e:
        mc_result = {"error": str(e)}

    return {
        "symbol":           symbol,
        "horizon_days":     horizon_days,
        "linear_forecast":  linear_result,
        "monte_carlo":      mc_result,
    }
