from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database.base import Base


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    event_type = Column(String, index=True) # war, sanctions, policy, economic
    severity = Column(Integer, index=True) # scale 1-10
    impact_label = Column(String, nullable=True) # CRITICAL, HIGH, ELEVATED
    source = Column(String)
    timestamp = Column(DateTime, index=True)
    country_id = Column(Integer, ForeignKey("country_risks.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    country = relationship("CountryRisk", back_populates="events")
