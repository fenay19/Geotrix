from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SignalBase(BaseModel):
    market_id: int
    event_id: Optional[int] = None
    signal_type: str
    confidence: float
    uncertainty: Optional[float] = None
    bullish_strength: Optional[float] = None
    bearish_strength: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    atr: Optional[float] = None
    max_position_size: Optional[float] = None
    volatility_level: Optional[str] = None
    reasoning: Optional[str] = None
    risk_factors: Optional[list] = None
    tags: Optional[list] = None

class SignalCreate(SignalBase):
    pass

class Signal(SignalBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
