from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.supply_chain_model import SupplyChainNode, SupplyChainDependency
from ..schemas.supply_chain_schema import SupplyChainNodeCreate, SupplyChainDependencyCreate


class SupplyChainRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Node methods ──
    def get_all_nodes(self) -> List[SupplyChainNode]:
        return self.db.query(SupplyChainNode).all()

    def get_node_by_id(self, node_id: int) -> Optional[SupplyChainNode]:
        return (
            self.db.query(SupplyChainNode)
            .filter(SupplyChainNode.id == node_id)
            .first()
        )

    def get_nodes_by_location(self, location: str) -> List[SupplyChainNode]:
        return (
            self.db.query(SupplyChainNode)
            .filter(SupplyChainNode.location == location)
            .all()
        )

    def create_node(self, node_in: SupplyChainNodeCreate) -> SupplyChainNode:
        db_node = SupplyChainNode(**node_in.model_dump())
        self.db.add(db_node)
        self.db.commit()
        self.db.refresh(db_node)
        return db_node

    # ── Dependency methods ──
    def get_all_dependencies(self) -> List[SupplyChainDependency]:
        return self.db.query(SupplyChainDependency).all()

    def get_dependencies_for_node(self, node_id: int) -> List[SupplyChainDependency]:
        """Get all dependencies where the given node is the source (outgoing)."""
        return (
            self.db.query(SupplyChainDependency)
            .filter(SupplyChainDependency.source_node_id == node_id)
            .all()
        )

    def get_dependents_of_node(self, node_id: int) -> List[SupplyChainDependency]:
        """Get all nodes that depend on the given node (incoming)."""
        return (
            self.db.query(SupplyChainDependency)
            .filter(SupplyChainDependency.target_node_id == node_id)
            .all()
        )

    def create_dependency(self, dep_in: SupplyChainDependencyCreate) -> SupplyChainDependency:
        db_dep = SupplyChainDependency(**dep_in.model_dump())
        self.db.add(db_dep)
        self.db.commit()
        self.db.refresh(db_dep)
        return db_dep
