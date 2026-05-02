from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database.base import Base

def _utcnow():
    """Timezone-aware UTC now; avoids the deprecated datetime.utcnow()."""
    return datetime.now(timezone.utc)

class TradingSignal(Base):
    __tablename__ = "trading_signals"
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True, index=True)
    signal_type = Column(String) # Enum-like: BUY/SELL/HOLD
    confidence = Column(Float)
    uncertainty = Column(Float, nullable=True) # 0 to 1
    bullish_strength = Column(Float, nullable=True) # 0 to 1
    bearish_strength = Column(Float, nullable=True) # 0 to 1
    entry_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    risk_reward_ratio = Column(Float, nullable=True) # e.g., 2.0
    signal_strength = Column(Float, nullable=True)
    atr = Column(Float, nullable=True) # Average True Range
    max_position_size = Column(Float, nullable=True) # Percentage
    volatility_level = Column(String, nullable=True) # Low, Medium, High
    reasoning = Column(String)
    risk_factors = Column(JSON, nullable=True) # JSON list
    tags = Column(JSON, nullable=True) # JSON list
    # ── Reliability Metrics (backtested / seeded) ─────────────────────────────
    signal_accuracy = Column(Float, nullable=True)          # Historical accuracy 0-1
    win_rate = Column(Float, nullable=True)                 # Win rate 0-1
    sharpe_ratio = Column(Float, nullable=True)             # Sharpe ratio value
    max_drawdown = Column(Float, nullable=True)             # Max drawdown 0-1
    annual_reliability_score = Column(Float, nullable=True) # Composite score 0-1
    triggering_event = Column(String, nullable=True)        # Geopolitical trigger label
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    market = relationship("Market", back_populates="signals")
    event = relationship("Event")