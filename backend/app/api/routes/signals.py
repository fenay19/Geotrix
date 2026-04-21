from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.signal_schema import Signal, SignalCreate
from ...services.signal_service import signal_service
from ...dependencies import get_db, get_current_user
from ...schemas.user_schema import User

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


@router.get("/{signal_id}", response_model=Signal)
def get_signal(signal_id: int, db: Session = Depends(get_db)):
    signal = signal_service.get_signal(db, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.post("/generate/{market_id}", response_model=Signal, status_code=201)
def generate_signal(market_id: int, db: Session = Depends(get_db)):
    """Auto-generates a trading signal using AI (OpenAI) with a rule-based fallback."""
    signal = signal_service.auto_generate_signal(db, market_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Market not found")
    return signal
