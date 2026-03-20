from sqlalchemy import Column, Integer, String, Float, DateTime
from ..database.base import Base

class TradingSignal(Base):
    __tablename__ = "trading_signals"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    signal_type = Column(String) # BUY/SELL
    confidence = Column(Float)
