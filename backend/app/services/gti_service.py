from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..models.event_model import Event
from ..repositories.risk_repo import GTIRepository
from ..schemas.gti_schema import GTIScoreCreate, GTIHistoryCreate


class GTIService:
    """
    Service to calculate and manage the Global Tension Index (GTI).
    """

    # Weights for different event types
    TYPE_WEIGHTS = {
        "war": 1.5,
        "conflict": 1.4,
        "sanctions": 1.2,
        "unrest": 1.1,
        "policy": 1.0,
        "economic": 0.8,
    }

    def calculate_current_gti(self, db: Session) -> float:
        """
        Calculates the current GTI based on events from the last 7 days.
        Formula: Avg(Severity * TypeWeight) normalized to 0-100.
        """
        seven_days_ago = datetime.utcnow() - timedelta(days=7)

        # Query events from the last 7 days directly
        events = (
            db.query(Event)
            .filter(Event.timestamp >= seven_days_ago)
            .order_by(Event.severity.desc())
            .limit(50)
            .all()
        )

        if not events:
            return 50.0  # Baseline neutral score

        total_weighted_severity = 0.0
        count = 0

        for event in events:
            event_type = (event.event_type or "").lower()
            weight = self.TYPE_WEIGHTS.get(event_type, 1.0)
            severity = event.severity or 5  # Default to mid-scale if null
            # Severity is 1-10, weight scales it further; max contribution = 10 * 1.5 * 10 = 150
            weighted_val = severity * weight * 10
            total_weighted_severity += weighted_val
            count += 1

        if count == 0:
            return 50.0

        raw_score = total_weighted_severity / count

        # Clamp between 0 and 100
        final_score = max(0.0, min(100.0, round(raw_score, 1)))
        severity_label = self.get_severity_label(final_score)

        # Save to DB
        gti_repo = GTIRepository(db)
        gti_in = GTIScoreCreate(current_score=final_score, severity_category=severity_label)
        gti_obj = gti_repo.upsert(gti_in)

        hist_in = GTIHistoryCreate(
            score=final_score,
            gti_id=gti_obj.id,
            timestamp=datetime.utcnow()
        )
        gti_repo.add_history(hist_in)

        return final_score

    def get_severity_label(self, score: float) -> str:
        if score < 30:
            return "LOW"
        elif score < 60:
            return "MODERATE"
        elif score < 80:
            return "HIGH"
        else:
            return "CRITICAL"


gti_service = GTIService()
