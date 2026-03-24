from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.supply_chain_schema import (
    SupplyChainNode, SupplyChainNodeCreate,
    SupplyChainDependency, SupplyChainDependencyCreate,
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
