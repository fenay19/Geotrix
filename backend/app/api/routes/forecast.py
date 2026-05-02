from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from ...dependencies import get_db
from ...services.market_service import market_service
from ...services.risk_service import risk_service
from ...ai.forecasting.price_forecaster import PriceForecaster
from ...config import settings

router = APIRouter()


@router.get("/{symbol}")
def get_price_forecast(
    symbol: str,
    horizon_days: int = Query(7, ge=1, le=30, description="Days to forecast"),
    db: Session = Depends(get_db)
):
    """
    Generates an AI-driven price forecast for a specific market asset.
    Uses recent OHLC history and current Global Tension Index (GTI) as context.
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
    gti_score = gti.current_score if gti else 50.0  # fixed: attribute is current_score, not score

    # 4. Convert history models to dicts for the forecaster
    candles = [
        {
            "close": h.close,   # fix: ORM column is 'close', not 'close_price'
            "high":  h.high,    # fix: ORM column is 'high', not 'high_price'
            "low":   h.low,     # fix: ORM column is 'low', not 'low_price'
            "open":  h.open,    # fix: ORM column is 'open', not 'open_price'
        }
        for h in reversed(history)  # Forecaster expects oldest -> newest
    ]

    # 5. Generate forecast — instantiate per-request to avoid shared-state race conditions
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
