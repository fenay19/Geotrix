from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class SimulationRunBase(BaseModel):
    scenario_name: str
    region: str
    event_type: str
    magnitude: str
    results: dict
    user_id: Optional[int] = None

class SimulationRunCreate(SimulationRunBase):
    pass

class SimulationRun(SimulationRunBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
