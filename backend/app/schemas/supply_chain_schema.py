from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

class SupplyChainNodeBase(BaseModel):
    name: str
    location: str
    type: Optional[str] = None

class SupplyChainNodeCreate(SupplyChainNodeBase):
    pass

class SupplyChainDependencyBase(BaseModel):
    source_node_id: int
    target_node_id: int
    dependency_type: str
    dependency_strength: Optional[float] = None

class SupplyChainDependencyCreate(SupplyChainDependencyBase):
    pass

class SupplyChainDependency(SupplyChainDependencyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SupplyChainNode(SupplyChainNodeBase):
    id: int
    outgoing_dependencies: List[SupplyChainDependency] = []
    incoming_dependencies: List[SupplyChainDependency] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ── Supply Chain Simulation Schemas ─────────────────────────────────────────

class SimulateRequest(BaseModel):
    node_id: int
    severity: float           # 0–100 disruption severity
    disruption_type: str = "Blockade"  # Blockade | Strike | Disaster
    apply_variability: bool = True     # whether to apply ±5% noise

class AffectedNodeResult(BaseModel):
    node_id: int
    name: str
    location: str
    node_type: str
    impact: float             # 0–100 computed disruption impact
    depth: int                # BFS depth from the source node
    dependency_strength: float  # strength of the edge that propagated to this node

class SimulationLog(BaseModel):
    step: int
    text: str
    type: str                 # "info" | "warn" | "crit"

class SimulateResponse(BaseModel):
    id: int
    source_node_id: int
    source_node_name: str
    severity: float
    disruption_type: str
    apply_variability: bool
    affected_nodes: List[AffectedNodeResult]
    logs: List[SimulationLog]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Node Intelligence Schemas ───────────────────────────────────────────────

class DependencyTreeNode(BaseModel):
    id: int
    name: str
    location: str
    type: str
    strength: Optional[float] = None
    dependency_type: Optional[str] = None
    children: List['DependencyTreeNode'] = []

    class Config:
        from_attributes = True

class ImpactPreviewItem(BaseModel):
    node_id: int
    name: str
    impact: float
    depth: int

class PropagationPathItem(BaseModel):
    target: str
    path: List[str]
    strength: float

class ChokepointAnalysisResult(BaseModel):
    is_chokepoint: bool
    chokepoint_score: float
    rank: int

class NodeOverview(BaseModel):
    id: int
    name: str
    location: str
    type: str

class NodeLiveContext(BaseModel):
    events: List[Any] = []
    markets: List[Any] = []
    gti_score: Optional[float] = None
    country_risk: Optional[Any] = None

class NodeIntelligenceResponse(BaseModel):
    overview: NodeOverview
    dependency_tree: Optional[DependencyTreeNode] = None
    live_context: NodeLiveContext
    impact_preview: dict  # maps "25", "50", "75", "100" -> List[ImpactPreviewItem]
    chokepoint_analysis: ChokepointAnalysisResult
    propagation_paths: List[PropagationPathItem]

# Rebuild forward references for recursive model
DependencyTreeNode.model_rebuild()


