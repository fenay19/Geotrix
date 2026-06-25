from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from ...schemas.simulation_schema import SimulationRun, SimulationRunCreate
from ...services.simulation_service import simulation_service
from ...dependencies import get_db, get_current_user
from ...schemas.user_schema import User

router = APIRouter()


class ScenarioRequest(BaseModel):
    scenario_name: str
    region: str
    event_type: str
    magnitude: str
    user_id: Optional[int] = None


@router.get("/", response_model=List[SimulationRun])
def get_simulations(user_id: Optional[int] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return simulation_service.get_simulations(db, user_id=user_id, skip=skip, limit=limit)


@router.post("/", response_model=SimulationRun, status_code=201)
def create_simulation(sim_in: SimulationRunCreate, db: Session = Depends(get_db)):
    return simulation_service.create_simulation(db, sim_in)


@router.get("/{run_id}", response_model=SimulationRun)
def get_simulation(run_id: int, db: Session = Depends(get_db)):
    sim = simulation_service.get_simulation(db, run_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return sim


@router.post("/run", response_model=SimulationRun, status_code=201)
def run_scenario(body: ScenarioRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Runs an AI-powered geopolitical scenario and returns market impact predictions."""
    return simulation_service.run_scenario(
        db,
        scenario_name=body.scenario_name,
        region=body.region,
        event_type=body.event_type,
        magnitude=body.magnitude,
        user_id=body.user_id,
    )
