from sqlalchemy.orm import Session
from ..models.supply_chain_model import SupplyChainNode

class SupplyChainRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, node_id: int):
        return self.db.query(SupplyChainNode).filter(SupplyChainNode.id == node_id).first()
