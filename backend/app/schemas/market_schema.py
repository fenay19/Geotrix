from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MarketBase(BaseModel):
    symbol: str
    price: float
    category: str
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
