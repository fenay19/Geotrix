from pydantic import BaseModel
from typing import List, Optional

class SupplyChainNodeBase(BaseModel):
    name: str
    location: str

class SupplyChainNode(SupplyChainNodeBase):
    id: int
    
    class Config:
        from_attributes = True
