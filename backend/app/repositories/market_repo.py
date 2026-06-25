from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.market_model import Market, MarketHistory
from ..schemas.market_schema import MarketCreate, MarketHistoryCreate


class MarketRepository:
    def __init__(self, db: Session):   
        self.db = db

    def get_all(self) -> List[Market]:
        return self.db.query(Market).all()

    def get_by_id(self, market_id: int) -> Optional[Market]:
        return self.db.query(Market).filter(Market.id == market_id).first()

    def get_global_assets(self, limit: int = 5) -> List[Market]:
        return (
            self.db.query(Market)
            .filter(Market.is_global == True)
            .limit(limit)
            .all()
        )

    def get_local_assets(self, country_id: int, limit: int = 3) -> List[Market]:
        return (
            self.db.query(Market)
            .filter(Market.country_id == country_id)
            .limit(limit)
            .all()
        )

    def get_by_symbol(self, symbol: str) -> Optional[Market]:
        return self.db.query(Market).filter(Market.symbol == symbol).first()

    def create(self, market_in: MarketCreate) -> Market:
        db_market = Market(**market_in.model_dump())
        self.db.add(db_market)
        self.db.commit()
        self.db.refresh(db_market)
        return db_market

    def update_price(self, symbol: str, new_price: float) -> Optional[Market]:
        market = self.get_by_symbol(symbol)
        if market:
            market.price = new_price
            self.db.commit()
            self.db.refresh(market)
        return market

    def add_history(self, history_in: MarketHistoryCreate) -> MarketHistory:
        db_history = MarketHistory(**history_in.model_dump())
        self.db.add(db_history)
        self.db.commit()
        self.db.refresh(db_history)
        return db_history

    def get_history(self, market_id: int, limit: int = 50) -> List[MarketHistory]:
        return (
            self.db.query(MarketHistory)
            .filter(MarketHistory.market_id == market_id)
            .order_by(MarketHistory.timestamp.desc())
            .limit(limit)
            .all()
        )

    def delete(self, market_id: int) -> bool:
        market = self.get_by_id(market_id)
        if market:
            self.db.delete(market)
            self.db.commit()
            return True
        return False
