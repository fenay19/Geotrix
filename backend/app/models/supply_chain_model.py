from sqlalchemy import Column, Integer, String
from ..database.base import Base

class SupplyChainNode(Base):
    __tablename__ = "supply_chain_nodes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    location = Column(String)
