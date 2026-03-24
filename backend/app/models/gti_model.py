from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from ..database.base import Base

class GTIScore(Base):
    __tablename__ = "gti_scores"
    id = Column(Integer, primary_key=True, index=True)
    current_score = Column(Float) # 0 to 100
    severity_category = Column(String) # Enum-like: Low, Moderate, High, Critical
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GTIHistory(Base):
    __tablename__ = "gti_history"
    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
