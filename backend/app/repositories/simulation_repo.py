from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.simulation_model import SimulationRun
from ..schemas.simulation_schema import SimulationRunCreate


class SimulationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, user_id: Optional[int] = None, skip: int = 0, limit: int = 50) -> List[SimulationRun]:
        query = self.db.query(SimulationRun)
        if user_id:
            query = query.filter(SimulationRun.user_id == user_id)
            
        return (
            query
            .order_by(SimulationRun.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_id(self, run_id: int) -> Optional[SimulationRun]:
        return (
            self.db.query(SimulationRun)
            .filter(SimulationRun.id == run_id)
            .first()
        )

    def create(self, sim_in: SimulationRunCreate) -> SimulationRun:
        db_sim = SimulationRun(**sim_in.model_dump())
        self.db.add(db_sim)
        self.db.commit()
        self.db.refresh(db_sim)
        return db_sim
