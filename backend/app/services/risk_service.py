from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List
from ..models.event_model import Event
from ..models.country_risk_model import CountryRisk
from ..repositories.risk_repo import CountryRiskRepository, GTIRepository
from ..schemas.country_risk_schema import CountryRiskCreate
from ..schemas.gti_schema import GTIScoreCreate, GTIHistoryCreate
from .gti_service import gti_service


class RiskService:

    def get_all_country_risks(self, db: Session):
        repo = CountryRiskRepository(db)
        return repo.get_all()

    def get_country_risk(self, db: Session, country_code: str):
        repo = CountryRiskRepository(db)
        return repo.get_by_code(country_code)

    def get_country_risk_by_id(self, db: Session, country_id: int):
        repo = CountryRiskRepository(db)
        return repo.get_by_id(country_id)

    def get_high_risk_countries(self, db: Session, min_score: float = 60.0):
        repo = CountryRiskRepository(db)
        return repo.get_high_risk(min_score)

    def upsert_country_risk(self, db: Session, risk_in: CountryRiskCreate):
        repo = CountryRiskRepository(db)
        return repo.upsert(risk_in)

    def recalculate_country_risk(self, db: Session, country_code: str) -> CountryRisk:
        """
        Dynamically recalculates a country's risk score based on its recent events
        using an exponential decay recency factor and threat sentiment weights.
        """
        import math
        repo = CountryRiskRepository(db)
        country = repo.get_by_code(country_code)
        if not country:
            return None

        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)
        events = (
            db.query(Event)
            .filter(Event.country_id == country.id)
            .filter(Event.timestamp >= seven_days_ago)
            .all()
        )

        if not events:
            # Gradually decay the score if no recent events exist
            new_score = max(25.0, round(country.risk_score * 0.90, 1))
        else:
            sentiment_map = {
                "war": 95.0,
                "conflict": 85.0,
                "sanctions": 75.0,
                "unrest": 65.0,
                "policy": 50.0,
                "economic": 40.0,
            }
            decay_lambda = 0.15
            
            total_score = 0.0
            total_weight = 0.0
            
            for event in events:
                # E = Event Severity (0 to 100)
                E = (event.severity or 5) * 10.0
                # S = Threat Sentiment
                S = sentiment_map.get((event.event_type or "").lower(), 50.0)
                
                # R = Recency Score (0 to 100)
                event_ts = event.timestamp
                if event_ts.tzinfo is None:
                    event_ts = event_ts.replace(tzinfo=timezone.utc)
                age_seconds = (now - event_ts).total_seconds()
                t = max(0.0, age_seconds / 86400.0)
                recency_weight = math.exp(-decay_lambda * t)
                R = recency_weight * 100.0
                
                # Combined country-level event score
                event_score = (0.50 * E) + (0.30 * S) + (0.20 * R)
                
                total_score += event_score * recency_weight
                total_weight += recency_weight
                
            if total_weight > 0:
                new_score = min(100.0, max(0.0, round(total_score / total_weight, 1)))
            else:
                new_score = 25.0

        new_color = self._classify_color(new_score)
        country.risk_score = new_score
        country.color_code = new_color
        country.last_updated = now
        db.commit()
        db.refresh(country)
        return country

    def get_globe_data(self, db: Session) -> List[dict]:
        """
        Returns all country risk records formatted for the Earth Globe frontend.
        Each entry includes country_code, risk_score, color_code, and sector_exposure.
        """
        repo = CountryRiskRepository(db)
        countries = repo.get_all()
        return [
            {
                "country_code": c.country_code,
                "country_name": c.country_name,
                "risk_score": c.risk_score,
                "color_code": c.color_code,
                "sector_exposure": c.sector_exposure or {},
            }
            for c in countries
        ]

    def _classify_color(self, score: float) -> str:
        if score < 35:
            return "Green"
        elif score < 65:
            return "Yellow"
        else:
            return "Red"

    # ── GTI pass-throughs ────────────────────────────────────────────────────
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

    def refresh_gti(self, db: Session) -> float:
        """Triggers a full GTI recalculation from live events."""
        return gti_service.calculate_current_gti(db)


risk_service = RiskService()
