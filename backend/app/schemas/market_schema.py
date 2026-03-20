from pydantic import BaseModel

class MarketBase(BaseModel):
    symbol: str
    price: float

class MarketUpdate(MarketBase):
    pass

class Market(MarketBase):
    id: int
    
    class Config:
        from_attributes = True
