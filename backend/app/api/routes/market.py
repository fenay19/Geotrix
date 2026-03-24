from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.market_schema import Market, MarketCreate, MarketHistory, MarketHistoryCreate
from ...services.market_service import market_service
from ...dependencies import get_db

router = APIRouter()


@router.get("/", response_model=List[Market])
def read_markets(db: Session = Depends(get_db)):
    return market_service.get_markets(db)


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
