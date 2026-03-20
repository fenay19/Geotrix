from pydantic import BaseModel
from datetime import datetime

class SignalBase(BaseModel):
    symbol: str
    signal_type: str
    confidence: float

class Signal(SignalBase):
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True
