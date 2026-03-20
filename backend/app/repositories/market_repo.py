from sqlalchemy.orm import Session
from ..models.market_model import Market

class MarketRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_symbol(self, symbol: str):
        return self.db.query(Market).filter(Market.symbol == symbol).first()
