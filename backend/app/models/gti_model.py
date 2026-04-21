from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
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
    history = relationship("GTIHistory", back_populates="gti_parent")

class GTIHistory(Base):
    __tablename__ = "gti_history"
    id = Column(Integer, primary_key=True, index=True)
    score = Column(Float)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    gti_id = Column(Integer, ForeignKey("gti_scores.id"), index=True)
    gti_parent = relationship("GTIScore", back_populates="history")
