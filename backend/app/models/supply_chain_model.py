from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database.base import Base

def _utcnow():
    return datetime.now(timezone.utc)

class SupplyChainNode(Base):
    __tablename__ = "supply_chain_nodes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    location = Column(String)
    type = Column(String)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    outgoing_dependencies = relationship("SupplyChainDependency", foreign_keys="SupplyChainDependency.source_node_id", back_populates="source_node")
    incoming_dependencies = relationship("SupplyChainDependency", foreign_keys="SupplyChainDependency.target_node_id", back_populates="target_node")

class SupplyChainDependency(Base):
    __tablename__ = "supply_chain_dependencies"
    id = Column(Integer, primary_key=True, index=True)
    source_node_id = Column(Integer, ForeignKey("supply_chain_nodes.id"), index=True)
    target_node_id = Column(Integer, ForeignKey("supply_chain_nodes.id"), index=True)
    dependency_type = Column(String)
    dependency_strength = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    source_node = relationship("SupplyChainNode", foreign_keys=[source_node_id], back_populates="outgoing_dependencies")
    target_node = relationship("SupplyChainNode", foreign_keys=[target_node_id], back_populates="incoming_dependencies")
