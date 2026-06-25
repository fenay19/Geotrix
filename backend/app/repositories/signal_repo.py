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
        data = signal_in.model_dump()
        # Only pass fields that actually correspond to columns in the database table
        valid_cols = {c.name for c in TradingSignal.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_cols}
        
        db_signal = TradingSignal(**filtered_data)
        self.db.add(db_signal)
        self.db.commit()
        self.db.refresh(db_signal)
        return db_signal
