from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.market_schema import Market, MarketCreate, MarketHistory, MarketHistoryCreate
from ...services.market_service import market_service
from ...dependencies import get_db
from ...pipelines.market_pipeline import market_pipeline

router = APIRouter()


@router.get("/", response_model=List[Market])
def read_markets(db: Session = Depends(get_db)):
    return market_service.get_markets(db)


@router.get("/global", response_model=List[Market])
def get_global_assets(limit: int = 5, db: Session = Depends(get_db)):
    return market_service.get_global_assets(db, limit)


@router.get("/local/{country_id}", response_model=List[Market])
def get_local_assets(country_id: int, limit: int = 3, db: Session = Depends(get_db)):
    return market_service.get_local_assets(db, country_id, limit)


@router.post("/", response_model=Market, status_code=201)
def create_market(market_in: MarketCreate, db: Session = Depends(get_db)):
    return market_service.create_market(db, market_in)


@router.get("/{symbol}", response_model=Market)
def read_market(symbol: str, db: Session = Depends(get_db)):
    market = market_service.get_market(db, symbol)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")
    return market


@router.post("/history", response_model=MarketHistory, status_code=201)
def add_market_history(history_in: MarketHistoryCreate, db: Session = Depends(get_db)):
    return market_service.add_market_history(db, history_in)


@router.post("/sync")
def sync_market_data(history_days: int = 30, db: Session = Depends(get_db)):
    """
    Triggers the Market Data Pipeline:
    - Fetches live price quotes from Finnhub for all registered markets.
    - Fetches and stores historical OHLC candle data for the past N days.
    Returns a summary of prices updated and candles inserted.
    """
    return market_pipeline.sync_all_markets(db, history_days=history_days)
