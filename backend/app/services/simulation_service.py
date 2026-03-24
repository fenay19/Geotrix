from sqlalchemy.orm import Session
from ..repositories.simulation_repo import SimulationRepository
from ..schemas.simulation_schema import SimulationRunCreate


class SimulationService:
    def get_simulations(self, db: Session, skip: int = 0, limit: int = 50):
        repo = SimulationRepository(db)
        return repo.get_all(skip=skip, limit=limit)

    def get_simulation(self, db: Session, run_id: int):
        repo = SimulationRepository(db)
        return repo.get_by_id(run_id)

    def create_simulation(self, db: Session, sim_in: SimulationRunCreate):
        repo = SimulationRepository(db)
        return repo.create(sim_in)


simulation_service = SimulationService()
