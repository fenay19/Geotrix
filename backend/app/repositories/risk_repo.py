from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.country_risk_model import CountryRisk
from ..models.gti_model import GTIScore, GTIHistory
from ..schemas.country_risk_schema import CountryRiskCreate
from ..schemas.gti_schema import GTIScoreCreate, GTIHistoryCreate


class CountryRiskRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[CountryRisk]:
        return self.db.query(CountryRisk).all()

    def get_by_code(self, country_code: str) -> Optional[CountryRisk]:
        return (
            self.db.query(CountryRisk)
            .filter(CountryRisk.country_code == country_code)
            .first()
        )

    def get_by_id(self, country_id: int) -> Optional[CountryRisk]:
        return self.db.query(CountryRisk).filter(CountryRisk.id == country_id).first()

    def upsert(self, risk_in: CountryRiskCreate) -> CountryRisk:
        existing = self.get_by_code(risk_in.country_code)
        if existing:
            for key, value in risk_in.model_dump().items():
                setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_risk = CountryRisk(**risk_in.model_dump())
            self.db.add(new_risk)
            self.db.commit()
            self.db.refresh(new_risk)
            return new_risk

    def get_high_risk(self, min_score: float = 60.0) -> List[CountryRisk]:
        return (
            self.db.query(CountryRisk)
            .filter(CountryRisk.risk_score >= min_score)
            .order_by(CountryRisk.risk_score.desc())
            .all()
        )


class GTIRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_latest(self) -> Optional[GTIScore]:
        return self.db.query(GTIScore).order_by(GTIScore.id.desc()).first()

    def upsert(self, gti_in: GTIScoreCreate) -> GTIScore:
        existing = self.get_latest()
        if existing:
            for key, value in gti_in.model_dump().items():
                setattr(existing, key, value)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_gti = GTIScore(**gti_in.model_dump())
            self.db.add(new_gti)
            self.db.commit()
            self.db.refresh(new_gti)
            return new_gti

    def add_history(self, history_in: GTIHistoryCreate) -> GTIHistory:
        new_hist = GTIHistory(**history_in.model_dump())
        self.db.add(new_hist)
        self.db.commit()
        self.db.refresh(new_hist)
        return new_hist

    def get_history(self, limit: int = 30) -> List[GTIHistory]:
        return (
            self.db.query(GTIHistory)
            .order_by(GTIHistory.timestamp.desc())
            .limit(limit)
            .all()
        )
