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


def test_gti_event_scaling(db):
    """
    With per-event normalisation, GTI should reflect average event *intensity*,
    not raw event count.

    Case 1 — quality beats quantity:
      5 minor skirmishes (severity=2) must score LOWER than 5 major war events (severity=9)
      even though the event count is identical.

    Case 2 — count-invariance:
      Adding 20 low-severity events to 1 extreme event must NOT produce a higher
      score than the 1 extreme event alone, because averaging dilutes the extremity.
    """
    us = CountryRisk(country_code="US", country_name="United States", risk_score=20.0, color_code="Green")
    db.add(us)
    db.commit()
    db.refresh(us)

    now = datetime.now(timezone.utc)

    # ── Case 1: 5 low-severity events ─────────────────────────────────────────
    for i in range(5):
        db.add(Event(
            title=f"Minor Skirmish {i}",
            description="Small border incident",
            event_type="war",
            severity=2,
            escalation_potential=2,
            impact_factor=1.0,
            timestamp=now - timedelta(hours=i),
            country_id=us.id,
        ))
    db.commit()
    gti_low = gti_service.calculate_current_gti(db)

    # ── Case 2: Replace with 5 high-severity events ────────────────────────────
    # Clear existing events by querying and deleting them
    db.query(Event).delete()
    db.commit()

    for i in range(5):
        db.add(Event(
            title=f"Major War Event {i}",
            description="Full-scale military offensive with heavy casualties",
            event_type="war",
            severity=9,
            escalation_potential=9,
            impact_factor=1.8,
            timestamp=now - timedelta(hours=i),
            country_id=us.id,
        ))
    db.commit()
    gti_high = gti_service.calculate_current_gti(db)

    # High-severity events must score strictly higher than low-severity events
    assert gti_high > gti_low, (
        f"Expected high-severity GTI ({gti_high}) > low-severity GTI ({gti_low})"
    )

    # ── Case 3: count-invariance — adding 20 minor events must not produce a ───
    # higher PILLAR SCORE than 1 extreme event alone. We check the raw pillar
    # breakdown (not EWMA-smoothed GTI) and clear GTI history between each sub-
    # scenario so Bayesian priors are not contaminated.
    db.query(Event).delete()
    db.query(GTIHistory).delete()
    db.query(GTIScore).delete()
    db.commit()

    # Single catastrophic event
    db.add(Event(
        title="Catastrophic Strike",
        description="Unprecedented military attack on a major city",
        event_type="war",
        severity=10,
        escalation_potential=10,
        impact_factor=2.0,
        timestamp=now - timedelta(minutes=10),
        country_id=us.id,
    ))
    db.commit()
    gti_service.calculate_current_gti(db)
    score_one = db.query(GTIScore).order_by(GTIScore.id.desc()).first()
    military_one = score_one.breakdown["military_risk"]

    # Clear history so priors don't contaminate the next run
    db.query(Event).delete()
    db.query(GTIHistory).delete()
    db.query(GTIScore).delete()
    db.commit()

    # Same catastrophic event + 20 noise events
    db.add(Event(
        title="Catastrophic Strike",
        description="Unprecedented military attack on a major city",
        event_type="war",
        severity=10,
        escalation_potential=10,
        impact_factor=2.0,
        timestamp=now - timedelta(minutes=10),
        country_id=us.id,
    ))
    for i in range(20):
        db.add(Event(
            title=f"Border Patrol Note {i}",
            description="Routine patrol activity",
            event_type="war",
            severity=1,
            escalation_potential=1,
            impact_factor=1.0,
            timestamp=now - timedelta(hours=i + 1),
            country_id=us.id,
        ))
    db.commit()
    gti_service.calculate_current_gti(db)
    score_diluted = db.query(GTIScore).order_by(GTIScore.id.desc()).first()
    military_diluted = score_diluted.breakdown["military_risk"]

    # Adding 20 noise events must dilute the military pillar score, not inflate it.
    # (Per-event normalization: average is pulled down by 20 low-severity events.)
    assert military_diluted < military_one, (
        f"Count-invariance violated: military pillar with 21 events ({military_diluted}) "
        f"should be less than with 1 extreme event ({military_one}), because the "
        f"20 noise events dilute the per-event average intensity."
    )




def test_deescalation_floor(db):
    us = CountryRisk(country_code="US", country_name="United States", risk_score=20.0, color_code="Green")
    db.add(us)
    db.commit()
    db.refresh(us)

    now = datetime.now(timezone.utc)

    # Seed multiple strong de-escalation events (ceasefires)
    for i in range(10):
        peace_event = Event(
            title=f"Ceasefire Accord {i}",
            description="De-escalation deal signed.",
            event_type="ceasefire",
            severity=8,
            escalation_potential=1,
            impact_factor=1.0,
            timestamp=now - timedelta(hours=i),
            country_id=us.id
        )
        db.add(peace_event)
    db.commit()

    # Calculate GTI
    gti_score = gti_service.calculate_current_gti(db)

    # Get breakdown to check military/diplomatic pillar scores
    latest_score = db.query(GTIScore).order_by(GTIScore.id.desc()).first()
    assert latest_score is not None
    
    # Check that diplomatic/military pillar score doesn't collapse below de-escalation floor
    for key in ["military_risk", "economic_warfare", "energy_risk", "cyber_risk", "diplomatic_risk", "political_risk"]:
        pillar_val = latest_score.breakdown.get(key, 50.0)
        assert pillar_val >= 10.0, f"{key} score collapsed below 10.0 floor: {pillar_val}"


def test_no_event_prior(db):
    # No events seeded at all. GTI should exactly equal the weighted sum of cold-start priors.
    gti_score = gti_service.calculate_current_gti(db)
    
    latest_score = db.query(GTIScore).order_by(GTIScore.id.desc()).first()
    assert latest_score is not None
    
    # Verify each pillar matches the prior exactly
    bd = latest_score.breakdown
    priors = bd["pillar_priors"]
    
    assert bd["military_risk"] == round(priors["military"], 1)
    assert bd["economic_warfare"] == round(priors["economic"], 1)
    assert bd["energy_risk"] == round(priors["energy"], 1)
    assert bd["cyber_risk"] == round(priors["cyber"], 1)
    assert bd["diplomatic_risk"] == round(priors["diplomatic"], 1)
    assert bd["political_risk"] == round(priors["political"], 1)

