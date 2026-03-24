from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.trading_signal_model import TradingSignal
from ..schemas.signal_schema import SignalCreate


class SignalRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 50) -> List[TradingSignal]:
        return (
            self.db.query(TradingSignal)
            .order_by(TradingSignal.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_id(self, signal_id: int) -> Optional[TradingSignal]:
        return (
            self.db.query(TradingSignal)
            .filter(TradingSignal.id == signal_id)
            .first()
        )

    def get_by_market(self, market_id: int) -> List[TradingSignal]:
        return (
            self.db.query(TradingSignal)
            .filter(TradingSignal.market_id == market_id)
            .order_by(TradingSignal.created_at.desc())
            .all()
        )

    def get_latest(self, market_id: int) -> Optional[TradingSignal]:
        return (
            self.db.query(TradingSignal)
            .filter(TradingSignal.market_id == market_id)
            .order_by(TradingSignal.id.desc())
            .first()
        )

    def create(self, signal_in: SignalCreate) -> TradingSignal:
        db_signal = TradingSignal(**signal_in.model_dump())
        self.db.add(db_signal)
        self.db.commit()
        self.db.refresh(db_signal)
        return db_signal
