from sqlalchemy.orm import Session
from ..repositories.signal_repo import SignalRepository
from ..schemas.signal_schema import SignalCreate


class SignalService:
    def get_signals(self, db: Session, skip: int = 0, limit: int = 50):
        repo = SignalRepository(db)
        return repo.get_all(skip=skip, limit=limit)

    def get_signal(self, db: Session, signal_id: int):
        repo = SignalRepository(db)
        return repo.get_by_id(signal_id)

    def get_signals_by_market(self, db: Session, market_id: int):
        repo = SignalRepository(db)
        return repo.get_by_market(market_id)

    def get_latest_signal(self, db: Session, market_id: int):
        repo = SignalRepository(db)
        return repo.get_latest(market_id)

    def create_signal(self, db: Session, signal_in: SignalCreate):
        repo = SignalRepository(db)
        return repo.create(signal_in)


signal_service = SignalService()
