from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MarketBase(BaseModel):
    symbol: str
    price: float

class MarketCreate(MarketBase):
    pass

class MarketUpdate(BaseModel):
    price: Optional[float] = None

class Market(MarketBase):
    id: int
    history: List['MarketHistory'] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MarketHistoryBase(BaseModel):
    market_id: int
    price: float
    timestamp: datetime

class MarketHistoryCreate(MarketHistoryBase):
    pass

class MarketHistory(MarketHistoryBase):
    id: int
    market_id: int

    class Config:
        from_attributes = True
