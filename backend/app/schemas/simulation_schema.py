from pydantic import BaseModel
from typing import List, Optional

class SimulationConfig(BaseModel):
    name: str
    scenario: str
    duration_days: int

class SimulationResult(BaseModel):
    id: int
    config: SimulationConfig
    outcome: str
