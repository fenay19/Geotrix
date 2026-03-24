from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.simulation_schema import SimulationRun, SimulationRunCreate
from ...services.simulation_service import simulation_service
from ...dependencies import get_db

router = APIRouter()


@router.get("/", response_model=List[SimulationRun])
def get_simulations(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return simulation_service.get_simulations(db, skip=skip, limit=limit)


@router.post("/", response_model=SimulationRun, status_code=201)
def create_simulation(sim_in: SimulationRunCreate, db: Session = Depends(get_db)):
    return simulation_service.create_simulation(db, sim_in)


@router.get("/{run_id}", response_model=SimulationRun)
def get_simulation(run_id: int, db: Session = Depends(get_db)):
    sim = simulation_service.get_simulation(db, run_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation run not found")
    return sim
