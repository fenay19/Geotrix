import pytest
from datetime import datetime, timedelta, timezone
from app.services.gti_service import gti_service
from app.models.country_risk_model import CountryRisk
from app.models.event_model import Event
from app.models.gti_model import GTIScore, GTIHistory

def test_calculate_current_gti(db):
    # 1. Seed countries with ISO codes referenced in the calculation
    us = CountryRisk(country_code="US", country_name="United States", risk_score=20.0, color_code="Green")
    ru = CountryRisk(country_code="RU", country_name="Russia", risk_score=80.0, color_code="Red")
    db.add(us)
    db.add(ru)
    db.commit()
    db.refresh(us)
    db.refresh(ru)

    # 2. Add realistic events from the last 2 days
    now = datetime.now(timezone.utc)
    
    # Event 1: Military conflict in RU (high influence, severe casualties, severe economic, severe infra, high escalation)
    event1 = Event(
        title="Major Conflict Escalation",
        description="Heavy shelling reported with multiple casualties and critical damage",
        event_type="war",
        severity=8,
        impact_label="CRITICAL",
        escalation_potential=9,
        impact_factor=1.75, # calculated from casualties=350, economic_damage=1200.0, infra=Severe, displaced=45000
        casualties=350,
        economic_damage=1200.0,
        infrastructure_destruction="Severe",
        displaced_population=45000,
        source="Reuters",
        timestamp=now - timedelta(hours=6),
        country_id=ru.id
    )

    # Event 2: Economic tariff decision in US (high influence, no casualties, moderate economic)
    event2 = Event(
        title="New Tariffs Imposed",
        description="US imposes tariffs on trade commodities",
        event_type="economic",
        severity=6,
        impact_label="HIGH",
        escalation_potential=5,
        impact_factor=1.15, # moderate economic damage
        casualties=0,
        economic_damage=150.0,
        infrastructure_destruction="Minimal",
        displaced_population=0,
        source="Bloomberg",
        timestamp=now - timedelta(days=1),
        country_id=us.id
    )

    db.add(event1)
    db.add(event2)
    db.commit()

    # 3. Calculate GTI
    gti_score = gti_service.calculate_current_gti(db)

    # 4. Assertions
    assert gti_score > 0
    assert gti_score <= 100

    # Verify that score is stored in DB
    latest_score = db.query(GTIScore).order_by(GTIScore.id.desc()).first()
    assert latest_score is not None
    assert latest_score.current_score == gti_score
    assert latest_score.breakdown is not None
    assert "global" in latest_score.breakdown
    assert "military_risk" in latest_score.breakdown
    assert "economic_warfare" in latest_score.breakdown

    # Verify history is added
    history = db.query(GTIHistory).order_by(GTIHistory.id.desc()).first()
    assert history is not None
    assert history.score == gti_score
    assert history.breakdown == latest_score.breakdown
