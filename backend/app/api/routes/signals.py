from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.signal_schema import Signal, SignalCreate, SignalWithMarket
from ...services.signal_service import signal_service
from ...dependencies import get_db, get_current_user
from ...schemas.user_schema import User
from ...models.trading_signal_model import TradingSignal
from ...models.market_model import Market
from sqlalchemy import desc

router = APIRouter()


@router.get("/", response_model=List[Signal])
def get_signals(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return signal_service.get_signals(db, skip=skip, limit=limit)


@router.post("/", response_model=Signal, status_code=201)
def create_signal(signal_in: SignalCreate, db: Session = Depends(get_db)):
    return signal_service.create_signal(db, signal_in)


@router.get("/market/{market_id}", response_model=List[Signal])
def get_signals_by_market(market_id: int, db: Session = Depends(get_db)):
    return signal_service.get_signals_by_market(db, market_id)


@router.get("/market/{market_id}/latest", response_model=Signal)
def get_latest_signal(market_id: int, db: Session = Depends(get_db)):
    signal = signal_service.get_latest_signal(db, market_id)
    if not signal:
        raise HTTPException(status_code=404, detail="No signal found for this market")
    return signal


@router.get("/with-market", response_model=List[SignalWithMarket])
def get_signals_with_market(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Returns the latest signal for each market, enriched with market metadata.
    Used by the AI Signals page list panel.
    """
    # Get the latest signal per market via a subquery approach
    from sqlalchemy import func

    subq = (
        db.query(
            TradingSignal.market_id,
            func.max(TradingSignal.created_at).label("max_created")
        )
        .group_by(TradingSignal.market_id)
        .subquery()
    )

    signals = (
        db.query(TradingSignal, Market)
        .join(subq, (TradingSignal.market_id == subq.c.market_id) &
                    (TradingSignal.created_at == subq.c.max_created))
        .join(Market, TradingSignal.market_id == Market.id)
        .order_by(desc(TradingSignal.confidence))
        .offset(skip).limit(limit)
        .all()
    )

    results = []
    for sig, mkt in signals:
        s = SignalWithMarket.model_validate(sig)
        s.market_symbol = mkt.symbol
        s.market_name = mkt.name
        s.market_price = mkt.price
        s.market_asset_class = mkt.asset_class
        s.market_geo_sensitivity = mkt.geo_sensitivity
        results.append(s)
    return results


@router.get("/by-class/{asset_class}", response_model=List[SignalWithMarket])
def get_signals_by_class(asset_class: str, db: Session = Depends(get_db)):
    """Latest signal per market filtered by asset class."""
    from sqlalchemy import func

    subq = (
        db.query(
            TradingSignal.market_id,
            func.max(TradingSignal.created_at).label("max_created")
        )
        .group_by(TradingSignal.market_id)
        .subquery()
    )

    signals = (
        db.query(TradingSignal, Market)
        .join(subq, (TradingSignal.market_id == subq.c.market_id) &
                    (TradingSignal.created_at == subq.c.max_created))
        .join(Market, TradingSignal.market_id == Market.id)
        .filter(Market.asset_class.ilike(asset_class))
        .order_by(desc(TradingSignal.confidence))
        .all()
    )

    results = []
    for sig, mkt in signals:
        s = SignalWithMarket.model_validate(sig)
        s.market_symbol = mkt.symbol
        s.market_name = mkt.name
        s.market_price = mkt.price
        s.market_asset_class = mkt.asset_class
        s.market_geo_sensitivity = mkt.geo_sensitivity
        results.append(s)
    return results


@router.get("/{signal_id}", response_model=Signal)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    signal = signal_service.get_signal(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.post("/generate/{market_id}", response_model=Signal, status_code=201)
def generate_signal(
    market_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-generates a trading signal using AI (OpenAI) with a rule-based fallback."""
    signal = signal_service.auto_generate_signal(db, market_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Market not found")
    return signal
