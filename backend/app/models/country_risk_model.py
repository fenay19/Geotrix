from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database.base import Base

def _utcnow():
    return datetime.now(timezone.utc)

class CountryRisk(Base):
    __tablename__ = "country_risks"
    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String, unique=True, index=True) # e.g., 'US', 'TW'
    country_name = Column(String)
    risk_score = Column(Float, index=True) # 0 to 100
    color_code = Column(String) # Enum-like: 'Red', 'Yellow', 'Green'
    sector_exposure = Column(JSON, nullable=True) # e.g., {"Energy": 55, "Defense": 25}
    last_updated = Column(DateTime(timezone=True), default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    events = relationship("Event", back_populates="country", cascade="all, delete-orphan")
