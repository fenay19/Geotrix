from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.country_risk_schema import CountryRisk, CountryRiskCreate
from ...schemas.gti_schema import GTIScore, GTIScoreCreate, GTIHistory, GTIHistoryCreate
from ...services.risk_service import risk_service
from ...dependencies import get_db, require_admin
from ...pipelines.risk_pipeline import risk_pipeline
from .ws import manager

router = APIRouter()


# ── Country Risk endpoints ──
@router.get("/countries", response_model=List[CountryRisk])
def get_all_country_risks(db: Session = Depends(get_db)):
    return risk_service.get_all_country_risks(db)


@router.get("/countries/high-risk", response_model=List[CountryRisk])
def get_high_risk_countries(min_score: float = 60.0, db: Session = Depends(get_db)):
    return risk_service.get_high_risk_countries(db, min_score)


@router.get("/countries/{country_identifier}", response_model=CountryRisk)
def get_country_risk(country_identifier: str, db: Session = Depends(get_db)):
    # Support lookup by numeric ID or country code (e.g. "US", "IN")
    if country_identifier.isdigit():
        risk = risk_service.get_country_risk_by_id(db, int(country_identifier))
    else:
        risk = risk_service.get_country_risk(db, country_identifier)
    if not risk:
        raise HTTPException(status_code=404, detail="Country risk not found")
    return risk


@router.post("/countries", response_model=CountryRisk, status_code=201)
def upsert_country_risk(risk_in: CountryRiskCreate, db: Session = Depends(get_db)):
    return risk_service.upsert_country_risk(db, risk_in)


# ── GTI endpoints ──
@router.get("/gti", response_model=GTIScore)
def get_latest_gti(db: Session = Depends(get_db)):
    gti = risk_service.get_latest_gti(db)
    if not gti:
        raise HTTPException(status_code=404, detail="GTI score not found")
    return gti


@router.post("/gti", response_model=GTIScore, status_code=201)
def upsert_gti(gti_in: GTIScoreCreate, db: Session = Depends(get_db)):
    return risk_service.upsert_gti(db, gti_in)


@router.get("/gti/history", response_model=List[GTIHistory])
def get_gti_history(limit: int = 30, db: Session = Depends(get_db)):
    return risk_service.get_gti_history(db, limit)


@router.post("/gti/history", response_model=GTIHistory, status_code=201)
def add_gti_history(history_in: GTIHistoryCreate, db: Session = Depends(get_db)):
    return risk_service.add_gti_history(db, history_in)


@router.post("/gti/refresh")
async def refresh_gti(db: Session = Depends(get_db)):
    """Triggers a full GTI recalculation from live event data."""
    score = risk_service.refresh_gti(db)
    await manager.broadcast({"type": "gti_update", "score": score})
    return {"message": "GTI refreshed", "new_score": score}


@router.get("/globe")
def get_globe_data(db: Session = Depends(get_db)):
    """Returns all country risk data formatted for the Earth Globe frontend."""
    return risk_service.get_globe_data(db)


@router.post("/countries/{country_code}/recalculate", response_model=CountryRisk)
def recalculate_country_risk(country_code: str, db: Session = Depends(get_db)):
    """Recalculates a single country's risk score based on its recent events."""
    result = risk_service.recalculate_country_risk(db, country_code)
    if not result:
        raise HTTPException(status_code=404, detail="Country not found")
    return result


@router.post("/sync")
async def sync_global_risk(include_ai_summary: bool = True, db: Session = Depends(get_db), admin=Depends(require_admin)):
    """
    Triggers the full Risk Intelligence Pipeline.
    Broadcats a 'risk_update' event to the frontend on completion.
    """
    result = risk_pipeline.sync_global_risk(db, include_ai_summary=include_ai_summary)
    await manager.broadcast({"type": "risk_update", "summary": result.get("ai_summary")})
    new_gti = result.get("new_gti")
    if new_gti is not None:
        try:
            await manager.broadcast({"type": "gti_update", "score": new_gti})
        except Exception:
            pass
    return result
