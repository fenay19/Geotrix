from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database.base import Base

class CountryRisk(Base):
    __tablename__ = "country_risks"
    id = Column(Integer, primary_key=True, index=True)
    country_code = Column(String, unique=True, index=True) # e.g., 'US', 'TW'
    country_name = Column(String)
    risk_score = Column(Float, index=True) # 0 to 100
    color_code = Column(String) # Enum-like: 'Red', 'Yellow', 'Green'
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    events = relationship("Event", back_populates="country", cascade="all, delete-orphan")
