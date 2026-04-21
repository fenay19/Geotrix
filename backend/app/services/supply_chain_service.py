from sqlalchemy.orm import Session
from typing import List, Optional
from ..repositories.supply_chain_repo import SupplyChainRepository
from ..schemas.supply_chain_schema import SupplyChainNodeCreate, SupplyChainDependencyCreate
from ..models.supply_chain_model import SupplyChainNode, SupplyChainDependency


class SupplyChainService:

    # ── Node operations ──────────────────────────────────────────────────────

    def get_all_nodes(self, db: Session) -> List[SupplyChainNode]:
        repo = SupplyChainRepository(db)
        return repo.get_all_nodes()

    def get_node(self, db: Session, node_id: int) -> Optional[SupplyChainNode]:
        repo = SupplyChainRepository(db)
        return repo.get_node_by_id(node_id)

    def get_nodes_by_location(self, db: Session, location: str) -> List[SupplyChainNode]:
        repo = SupplyChainRepository(db)
        return repo.get_nodes_by_location(location)

    def create_node(self, db: Session, node_in: SupplyChainNodeCreate) -> SupplyChainNode:
        repo = SupplyChainRepository(db)
        return repo.create_node(node_in)

    # ── Dependency operations ────────────────────────────────────────────────

    def get_dependencies(self, db: Session, node_id: int) -> List[SupplyChainDependency]:
        repo = SupplyChainRepository(db)
        return repo.get_dependencies_for_node(node_id)

    def get_dependents(self, db: Session, node_id: int) -> List[SupplyChainDependency]:
        repo = SupplyChainRepository(db)
        return repo.get_dependents_of_node(node_id)

    def create_dependency(self, db: Session, dep_in: SupplyChainDependencyCreate) -> SupplyChainDependency:
        repo = SupplyChainRepository(db)
        return repo.create_dependency(dep_in)

    # ── Analytics ───────────────────────────────────────────────────────────

    def get_risk_graph(self, db: Session) -> dict:
        """
        Returns the full supply chain as a graph structure:
        { nodes: [...], edges: [...] }
        Ready for D3 / vis.js / react-flow visualizations on the frontend.
        """
        repo = SupplyChainRepository(db)
        nodes = repo.get_all_nodes()
        edges = repo.get_all_dependencies()

        return {
            "nodes": [
                {
                    "id": n.id,
                    "label": n.name,
                    "location": n.location,
                    "type": n.type,
                }
                for n in nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_node_id,
                    "target": e.target_node_id,
                    "type": e.dependency_type,
                    "strength": e.dependency_strength,
                }
                for e in edges
            ],
        }

    def get_critical_nodes(self, db: Session, min_dependents: int = 2) -> List[dict]:
        """
        Identifies "critical" supply chain nodes — those that many others depend on.
        Returns nodes with their dependent count (highest risk to disrupt).
        """
        repo = SupplyChainRepository(db)
        nodes = repo.get_all_nodes()
        all_deps = repo.get_all_dependencies()

        # Count how many nodes depend on each node (incoming edges)
        dep_count: dict = {}
        for dep in all_deps:
            dep_count[dep.target_node_id] = dep_count.get(dep.target_node_id, 0) + 1

        critical = []
        for node in nodes:
            count = dep_count.get(node.id, 0)
            if count >= min_dependents:
                critical.append({
                    "id": node.id,
                    "name": node.name,
                    "location": node.location,
                    "type": node.type,
                    "dependent_count": count,
                    "risk_label": "CRITICAL" if count >= 4 else "HIGH",
                })

        # Sort by most depended-on first
        return sorted(critical, key=lambda x: x["dependent_count"], reverse=True)


supply_chain_service = SupplyChainService()
