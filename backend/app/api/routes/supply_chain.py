from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ...schemas.supply_chain_schema import (
    SupplyChainNode, SupplyChainNodeCreate,
    SupplyChainDependency, SupplyChainDependencyCreate,
    SimulateRequest, SimulateResponse,
    NodeIntelligenceResponse,
)
from ...services.supply_chain_service import supply_chain_service
from ...dependencies import get_db

router = APIRouter()


# ── Node endpoints ──

@router.get("/nodes", response_model=List[SupplyChainNode])
def get_all_nodes(db: Session = Depends(get_db)):
    return supply_chain_service.get_all_nodes(db)


@router.post("/nodes", response_model=SupplyChainNode, status_code=201)
def create_node(node_in: SupplyChainNodeCreate, db: Session = Depends(get_db)):
    return supply_chain_service.create_node(db, node_in)


@router.get("/nodes/location/{location}", response_model=List[SupplyChainNode])
def get_nodes_by_location(location: str, db: Session = Depends(get_db)):
    return supply_chain_service.get_nodes_by_location(db, location)


@router.get("/nodes/{node_id}", response_model=SupplyChainNode)
def get_node(node_id: int, db: Session = Depends(get_db)):
    node = supply_chain_service.get_node(db, node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Supply chain node not found")
    return node


# ── Dependency endpoints ──

@router.get("/nodes/{node_id}/dependencies", response_model=List[SupplyChainDependency])
def get_dependencies(node_id: int, db: Session = Depends(get_db)):
    return supply_chain_service.get_dependencies(db, node_id)


@router.get("/nodes/{node_id}/dependents", response_model=List[SupplyChainDependency])
def get_dependents(node_id: int, db: Session = Depends(get_db)):
    return supply_chain_service.get_dependents(db, node_id)


@router.post("/dependencies", response_model=SupplyChainDependency, status_code=201)
def create_dependency(dep_in: SupplyChainDependencyCreate, db: Session = Depends(get_db)):
    return supply_chain_service.create_dependency(db, dep_in)


# ── Graph analytics ──

@router.get("/graph")
def get_risk_graph(
    location: Optional[str] = None,
    node_type: Optional[str] = None,
    min_strength: Optional[float] = None,
    dependency_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns the supply chain as a nodes+edges graph, with optional filtering:
    - location: filter nodes by location (e.g. Taiwan, China, Saudi Arabia)
    - node_type: filter nodes by type (resource, industry)
    - min_strength: filter connections by minimum dependency strength (0.0 to 1.0)
    - dependency_type: filter connections by type (critical_input, major_input)
    """
    return supply_chain_service.get_risk_graph(
        db,
        location=location,
        node_type=node_type,
        min_strength=min_strength,
        dependency_type=dependency_type,
    )


@router.get("/critical-nodes")
def get_critical_nodes(
    min_score: Optional[float] = None,
    min_dependents: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Returns nodes identified as chokepoints based on sum of outgoing dependency strengths."""
    score_threshold = 0.5
    if min_score is not None:
        score_threshold = min_score
    elif min_dependents is not None:
        score_threshold = 0.5 * min_dependents

    return supply_chain_service.get_critical_nodes(db, score_threshold)


@router.get("/nodes/{node_id}/intelligence", response_model=NodeIntelligenceResponse)
def get_node_intelligence(node_id: int, db: Session = Depends(get_db)):
    """
    Returns aggregated intelligence for a supply chain node including:
    - Basic overview details
    - Downstream dependency tree
    - Live context matching keywords (events, markets, GTI, risk)
    - Cascade impact preview at different severities
    - Chokepoint analysis and rankings
    - Fully traced propagation paths
    """
    try:
        return supply_chain_service.get_node_intelligence(db, node_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── BFS Impact Propagation Simulation ──

@router.post("/simulate", response_model=SimulateResponse, status_code=201)
def simulate_disruption(body: SimulateRequest, db: Session = Depends(get_db)):
    """
    Runs a real BFS graph-based impact propagation simulation.

    - node_id:             ID of the supply chain node to disrupt
    - severity:            Disruption severity 0–100
    - disruption_type:     'Blockade' | 'Strike' | 'Disaster'
    - apply_variability:   Apply ±5% stochastic noise to each propagation step

    Returns the full propagation result including affected nodes with
    computed impact scores and step-by-step simulation logs.
    """
    try:
        return supply_chain_service.run_supply_chain_simulation(db, body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/simulations")
def get_simulation_history(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Returns recent supply chain simulation runs, most recent first."""
    return supply_chain_service.get_simulation_history(db, skip=skip, limit=limit)
