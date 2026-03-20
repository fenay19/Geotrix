from sqlalchemy import Column, Integer, String, Float
from ..database.base import Base

class Market(Base):
    __tablename__ = "markets"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, unique=True, index=True)
    price = Column(Float)
