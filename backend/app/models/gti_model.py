from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database.base import Base

def _utcnow():
    return datetime.now(timezone.utc)

class GTIScore(Base):
    __tablename__ = "gti_scores"
    id = Column(Integer, primary_key=True, index=True)
    current_score = Column(Float) # 0 to 100
    severity_category = Column(String) # Enum-like: Low, Moderate, High, Critical
    breakdown = Column(JSON, nullable=True) # e.g. {"military": 85.0, "economic": 68.0, ...}
    last_updated = Column(DateTime(timezone=True), default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    history = relationship("GTIHistory", back_populates="gti_parent")

class GTIHistory(Base):
    __tablename__ = "gti_history"
    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float)
    breakdown = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), index=True, default=_utcnow)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    gti_id = Column(Integer, ForeignKey("gti_scores.id"), index=True)
    gti_parent = relationship("GTIScore", back_populates="history")
