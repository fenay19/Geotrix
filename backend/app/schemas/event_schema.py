from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[int] = None
    impact_label: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    country_id: Optional[int] = None


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    """Partial update schema — all fields optional."""
    title: Optional[str] = None
    description: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[int] = None
    impact_label: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    country_id: Optional[int] = None


class Event(EventBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
