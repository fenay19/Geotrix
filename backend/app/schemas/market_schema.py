from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MarketBase(BaseModel):
    symbol: str
    name: Optional[str] = None
    price: float
    category: str
    asset_class: Optional[str] = None   # Stocks|ETFs|Forex|Crypto|Commodities|Bonds|Indices
    geo_sensitivity: Optional[float] = None  # 0.0-1.0
    is_global: bool = False
    country_id: Optional[int] = None

class MarketCreate(MarketBase):
    pass

class MarketUpdate(BaseModel):
    price: Optional[float] = None

class MarketHistoryBase(BaseModel):
    market_id: int
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    timestamp: datetime

class MarketHistoryCreate(MarketHistoryBase):
    pass

class MarketHistory(MarketHistoryBase):
    id: int
    market_id: int

    class Config:
        from_attributes = True

class Market(MarketBase):
    id: int
    history: List[MarketHistory] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MarketWithSignal(BaseModel):
    """Lightweight market + latest signal summary for Signals list page."""
    id: int
    symbol: str
    name: Optional[str] = None
    price: Optional[float] = None
    asset_class: Optional[str] = None
    geo_sensitivity: Optional[float] = None
    latest_signal_type: Optional[str] = None
    latest_signal_confidence: Optional[float] = None
    latest_signal_id: Optional[int] = None

    class Config:
        from_attributes = True
