from sqlalchemy.orm import Session
from ..repositories.risk_repo import CountryRiskRepository, GTIRepository
from ..schemas.country_risk_schema import CountryRiskCreate
from ..schemas.gti_schema import GTIScoreCreate, GTIHistoryCreate


class RiskService:
    def get_all_country_risks(self, db: Session):
        repo = CountryRiskRepository(db)
        return repo.get_all()

    def get_country_risk(self, db: Session, country_code: str):
        repo = CountryRiskRepository(db)
        return repo.get_by_code(country_code)

    def get_high_risk_countries(self, db: Session, min_score: float = 60.0):
        repo = CountryRiskRepository(db)
        return repo.get_high_risk(min_score)

    def upsert_country_risk(self, db: Session, risk_in: CountryRiskCreate):
        repo = CountryRiskRepository(db)
        return repo.upsert(risk_in)

    def get_latest_gti(self, db: Session):
        repo = GTIRepository(db)
        return repo.get_latest()

    def upsert_gti(self, db: Session, gti_in: GTIScoreCreate):
        repo = GTIRepository(db)
        return repo.upsert(gti_in)

    def add_gti_history(self, db: Session, history_in: GTIHistoryCreate):
        repo = GTIRepository(db)
        return repo.add_history(history_in)

    def get_gti_history(self, db: Session, limit: int = 30):
        repo = GTIRepository(db)
        return repo.get_history(limit)


risk_service = RiskService()
