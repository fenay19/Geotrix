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


def _enrich_signal(db: Session, sig: TradingSignal, response_class=Signal, history=None):
    s = response_class.model_validate(sig)
    vol_map = {"Low": 0.10, "Medium": 0.18, "High": 0.30}
    vol_val = vol_map.get(sig.volatility_level, 0.18)
    metrics = signal_service.calculate_reliability_metrics(db, sig.market_id, vol_val, history=history)
    s.win_rate = metrics["win_rate"]
    s.avg_return = metrics["avg_return"]
    s.hold_days = metrics["hold_days"]
    s.total_runs = metrics["total_runs"]
    s.past_signals = metrics["past_signals"]
    return s


@router.get("/", response_model=List[Signal])
def get_signals(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    db_signals = signal_service.get_signals(db, skip=skip, limit=limit)
    return [_enrich_signal(db, sig, Signal) for sig in db_signals]


@router.post("/", response_model=Signal, status_code=201)
def create_signal(signal_in: SignalCreate, db: Session = Depends(get_db)):
    sig = signal_service.create_signal(db, signal_in)
    return _enrich_signal(db, sig, Signal)


@router.get("/market/{market_id}", response_model=List[Signal])
def get_signals_by_market(market_id: int, db: Session = Depends(get_db)):
    db_signals = signal_service.get_signals_by_market(db, market_id)
    return [_enrich_signal(db, sig, Signal) for sig in db_signals]


@router.get("/market/{market_id}/latest", response_model=Signal)
def get_latest_signal(market_id: int, db: Session = Depends(get_db)):
    sig = signal_service.get_latest_signal(db, market_id)
    if not sig:
        raise HTTPException(status_code=404, detail="No signal found for this market")
    return _enrich_signal(db, sig, Signal)


@router.get("/with-market", response_model=List[SignalWithMarket])
def get_signals_with_market(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Returns the latest signal for each market, enriched with market metadata.
    Used by the AI Signals page list panel.
    """
    # Get the latest signal per market via a subquery approach
    from sqlalchemy import func
    from ...models.market_model import MarketHistory

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

    # Bulk fetch all MarketHistory in a single query
    all_history = db.query(MarketHistory).order_by(MarketHistory.market_id, MarketHistory.timestamp.desc()).all()
    history_by_market = {}
    for h in all_history:
        if h.market_id not in history_by_market:
            history_by_market[h.market_id] = []
        if len(history_by_market[h.market_id]) < 180:
            history_by_market[h.market_id].append(h)

    results = []
    for sig, mkt in signals:
        mkt_history = history_by_market.get(sig.market_id, [])
        s = _enrich_signal(db, sig, SignalWithMarket, history=mkt_history)
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
    from ...models.market_model import MarketHistory

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

    # Bulk fetch all MarketHistory in a single query
    all_history = db.query(MarketHistory).order_by(MarketHistory.market_id, MarketHistory.timestamp.desc()).all()
    history_by_market = {}
    for h in all_history:
        if h.market_id not in history_by_market:
            history_by_market[h.market_id] = []
        if len(history_by_market[h.market_id]) < 180:
            history_by_market[h.market_id].append(h)

    results = []
    for sig, mkt in signals:
        mkt_history = history_by_market.get(sig.market_id, [])
        s = _enrich_signal(db, sig, SignalWithMarket, history=mkt_history)
        s.market_symbol = mkt.symbol
        s.market_name = mkt.name
        s.market_price = mkt.price
        s.market_asset_class = mkt.asset_class
        s.market_geo_sensitivity = mkt.geo_sensitivity
        results.append(s)
    return results


@router.get("/{signal_id}", response_model=Signal)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    sig = signal_service.get_signal(db, signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    return _enrich_signal(db, sig, Signal)


@router.post("/generate/{market_id}", response_model=Signal, status_code=201)
def generate_signal(
    market_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-generates a trading signal using AI (OpenAI) with a rule-based fallback."""
    sig = signal_service.auto_generate_signal(db, market_id)
    if not sig:
        raise HTTPException(status_code=404, detail="Market not found")
    return _enrich_signal(db, sig, Signal)


from fastapi import BackgroundTasks

def generate_all_signals_task():
    # Open a local Session for the background thread
    from ...database.db import SessionLocal
    db = SessionLocal()
    try:
        markets = db.query(Market).all()
        logger.info("Background task: Starting bulk signal generation for %d markets.", len(markets))
        for m in markets:
            try:
                signal_service.auto_generate_signal(db, m.id)
            except Exception as e:
                logger.error("Background task: Failed to generate signal for market %s: %s", m.symbol, e)
        logger.info("Background task: Bulk signal generation complete.")
    finally:
        db.close()


@router.post("/generate-all", status_code=202)
def generate_all_signals(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Triggers background generation of trading signals for all markets."""
    background_tasks.add_task(generate_all_signals_task)
    return {"message": "Background generation of all signals triggered."}
