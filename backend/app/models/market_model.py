from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database.base import Base

def _utcnow():
    return datetime.now(timezone.utc)

class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    name = Column(String, nullable=True)            # Display name e.g. "S&P 500 SPDR ETF"
    price = Column(Float)
    category = Column(String) # 'Commodity', 'Index', 'Currency'
    asset_class = Column(String, nullable=True)     # Stocks|ETFs|Forex|Crypto|Commodities|Bonds|Indices
    geo_sensitivity = Column(Float, nullable=True)  # 0.0-1.0 geopolitical sensitivity
    is_global = Column(Boolean, default=False)
    country_id = Column(Integer, ForeignKey("country_risks.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    country = relationship("CountryRisk")
    history = relationship("MarketHistory", back_populates="market", cascade="all, delete-orphan")
    signals = relationship("TradingSignal", back_populates="market")

class MarketHistory(Base):
    __tablename__ = "market_history"
    id = Column(Integer, primary_key=True, index=True)
    market_id = Column(Integer, ForeignKey("markets.id"), index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), index=True, default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    market = relationship("Market", back_populates="history")
