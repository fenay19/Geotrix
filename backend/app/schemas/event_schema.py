from pydantic import BaseModel
from datetime import datetime

class EventBase(BaseModel):
    title: str
    description: str

class EventCreate(EventBase):
    pass

class Event(EventBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True
