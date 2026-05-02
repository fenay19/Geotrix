from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database.base import Base

def _utcnow():
    return datetime.now(timezone.utc)

class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    event_type = Column(String, index=True) # war, sanctions, policy, economic
    severity = Column(Integer, index=True) # scale 1-10
    impact_label = Column(String, nullable=True) # CRITICAL, HIGH, ELEVATED
    escalation_potential = Column(Integer, default=3)
    impact_factor = Column(Float, default=1.0)
    casualties = Column(Integer, nullable=True, default=0)
    economic_damage = Column(Float, nullable=True, default=0.0) # in millions of USD
    infrastructure_destruction = Column(String, nullable=True, default="Minimal")
    displaced_population = Column(Integer, nullable=True, default=0)
    source = Column(String)
    timestamp = Column(DateTime(timezone=True), index=True)
    country_id = Column(Integer, ForeignKey("country_risks.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    country = relationship("CountryRisk", back_populates="events")
