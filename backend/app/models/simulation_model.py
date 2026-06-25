from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database.base import Base

def _utcnow():
    return datetime.now(timezone.utc)

class SimulationRun(Base):
    __tablename__ = "simulation_runs"
    id = Column(Integer, primary_key=True, index=True)
    scenario_name = Column(String) # e.g. "Taiwan Conflict"
    region = Column(String)
    event_type = Column(String)
    magnitude = Column(String) # e.g. "Severe"
    results = Column(JSON) # JSON object containing predicted impacts on assets/sectors
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)

    user = relationship("User", back_populates="simulation_runs")
