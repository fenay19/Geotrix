from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.supply_chain_model import SupplyChainNode, SupplyChainDependency, SupplyChainSimulationRun
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

    # ── BFS helpers: bulk-load entire adjacency list in 2 queries ──────────

    def get_all_nodes_map(self) -> dict:
        """Returns {node_id: SupplyChainNode} for the entire graph."""
        return {n.id: n for n in self.db.query(SupplyChainNode).all()}

    def get_adjacency_map(self) -> dict:
        """
        Returns {source_node_id: [SupplyChainDependency, ...]} for the entire graph.
        Loading all edges in one query is far more efficient than per-node lookups
        inside the BFS loop.
        """
        adj: dict = {}
        for dep in self.db.query(SupplyChainDependency).all():
            adj.setdefault(dep.source_node_id, []).append(dep)
        return adj

    # ── Simulation run persistence ──────────────────────────────────────────

    def create_simulation_run(
        self,
        source_node_id: int,
        source_node_name: str,
        severity: float,
        disruption_type: str,
        apply_variability: bool,
        affected_nodes_json: list,
        logs_json: list,
    ) -> SupplyChainSimulationRun:
        run = SupplyChainSimulationRun(
            source_node_id=source_node_id,
            source_node_name=source_node_name,
            severity=severity,
            disruption_type=disruption_type,
            apply_variability=apply_variability,
            affected_nodes_json=affected_nodes_json,
            logs_json=logs_json,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_simulation_run_by_id(self, run_id: int) -> Optional[SupplyChainSimulationRun]:
        return (
            self.db.query(SupplyChainSimulationRun)
            .filter(SupplyChainSimulationRun.id == run_id)
            .first()
        )

    def get_simulation_runs(
        self, skip: int = 0, limit: int = 20
    ) -> List[SupplyChainSimulationRun]:
        return (
            self.db.query(SupplyChainSimulationRun)
            .order_by(SupplyChainSimulationRun.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

