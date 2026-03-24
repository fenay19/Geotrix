from sqlalchemy.orm import Session
from ..repositories.market_repo import MarketRepository
from ..schemas.market_schema import MarketCreate, MarketHistoryCreate


class MarketService:
    def get_markets(self, db: Session):
        repo = MarketRepository(db)
        return repo.get_all()

    def get_market(self, db: Session, symbol: str):
        repo = MarketRepository(db)
        return repo.get_by_symbol(symbol)

    def create_market(self, db: Session, market_in: MarketCreate):
        repo = MarketRepository(db)
        return repo.create(market_in)

    def update_price(self, db: Session, symbol: str, new_price: float):
        repo = MarketRepository(db)
        return repo.update_price(symbol, new_price)

    def get_history(self, db: Session, market_id: int, limit: int = 50):
        repo = MarketRepository(db)
        return repo.get_history(market_id, limit)

    def add_market_history(self, db: Session, history_in: MarketHistoryCreate):
        repo = MarketRepository(db)
        return repo.add_history(history_in)


market_service = MarketService()
