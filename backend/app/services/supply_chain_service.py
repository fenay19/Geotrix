from sqlalchemy.orm import Session
from ..repositories.supply_chain_repo import SupplyChainRepository
from ..schemas.supply_chain_schema import SupplyChainNodeCreate, SupplyChainDependencyCreate


class SupplyChainService:
    def get_all_nodes(self, db: Session):
        repo = SupplyChainRepository(db)
        return repo.get_all_nodes()

    def get_node(self, db: Session, node_id: int):
        repo = SupplyChainRepository(db)
        return repo.get_node_by_id(node_id)

    def get_nodes_by_location(self, db: Session, location: str):
        repo = SupplyChainRepository(db)
        return repo.get_nodes_by_location(location)

    def create_node(self, db: Session, node_in: SupplyChainNodeCreate):
        repo = SupplyChainRepository(db)
        return repo.create_node(node_in)

    def get_dependencies(self, db: Session, node_id: int):
        repo = SupplyChainRepository(db)
        return repo.get_dependencies_for_node(node_id)

    def get_dependents(self, db: Session, node_id: int):
        repo = SupplyChainRepository(db)
        return repo.get_dependents_of_node(node_id)

    def create_dependency(self, db: Session, dep_in: SupplyChainDependencyCreate):
        repo = SupplyChainRepository(db)
        return repo.create_dependency(dep_in)


supply_chain_service = SupplyChainService()
