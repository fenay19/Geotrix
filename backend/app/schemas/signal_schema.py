from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SignalBase(BaseModel):
    market_id: int
    event_id: Optional[int] = None
    signal_type: str
    confidence: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    reasoning: Optional[str] = None

class SignalCreate(SignalBase):
    pass

class Signal(SignalBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
