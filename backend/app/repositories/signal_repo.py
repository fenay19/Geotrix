from sqlalchemy.orm import Session
from ..models.trading_signal_model import TradingSignal

class SignalRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_latest(self, symbol: str):
        return self.db.query(TradingSignal).filter(TradingSignal.symbol == symbol).order_by(TradingSignal.id.desc()).first()
