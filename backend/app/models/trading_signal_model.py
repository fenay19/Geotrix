from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database.base import Base

class TradingSignal(Base):
    __tablename__ = "trading_signals"
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    signal_type = Column(String) # Enum-like: BUY/SELL
    confidence = Column(Float)
    uncertainty = Column(Float, nullable=True) # 0 to 1
    bullish_strength = Column(Float, nullable=True) # 0 to 1
    bearish_strength = Column(Float, nullable=True) # 0 to 1
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True) # e.g., 2.0
    atr = Column(Float, nullable=True) # Average True Range
    max_position_size = Column(Float, nullable=True) # Percentage
    volatility_level = Column(String, nullable=True) # Low, Medium, High
    reasoning = Column(String)
    risk_factors = Column(JSON, nullable=True) # JSON list
    tags = Column(JSON, nullable=True) # JSON list
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    market = relationship("Market", back_populates="signals")
    event = relationship("Event")
    