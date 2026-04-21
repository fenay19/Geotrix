from pydantic import BaseModel
from typing import List, Optional
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
