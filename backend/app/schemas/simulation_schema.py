from pydantic import BaseModel
from typing import List, Optional

class SimulationRunBase(BaseModel):
    scenario_name: str
    region: str
    event_type: str
    magnitude: str
    results: dict

class SimulationRunCreate(SimulationRunBase):
    pass

class SimulationRun(SimulationRunBase):
    id: int
    created_at: str

    class Config:
        from_attributes = True
