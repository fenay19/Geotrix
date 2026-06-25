from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    event_type: Optional[str] = None
    severity: Optional[int] = None
    impact_label: Optional[str] = None
    escalation_potential: Optional[int] = None
    impact_factor: Optional[float] = None
    casualties: Optional[int] = 0
    economic_damage: Optional[float] = 0.0
    infrastructure_destruction: Optional[str] = "Minimal"
    displaced_population: Optional[int] = 0
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
    escalation_potential: Optional[int] = None
    impact_factor: Optional[float] = None
    casualties: Optional[int] = None
    economic_damage: Optional[float] = None
    infrastructure_destruction: Optional[str] = None
    displaced_population: Optional[int] = None
    source: Optional[str] = None
    timestamp: Optional[datetime] = None
    country_id: Optional[int] = None


class Event(EventBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
