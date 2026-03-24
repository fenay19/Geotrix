from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.country_risk_schema import CountryRisk, CountryRiskCreate
from ...schemas.gti_schema import GTIScore, GTIScoreCreate, GTIHistory, GTIHistoryCreate
from ...services.risk_service import risk_service
from ...dependencies import get_db

router = APIRouter()


# ── Country Risk endpoints ──
@router.get("/countries", response_model=List[CountryRisk])
def get_all_country_risks(db: Session = Depends(get_db)):
    return risk_service.get_all_country_risks(db)


@router.get("/countries/high-risk", response_model=List[CountryRisk])
def get_high_risk_countries(min_score: float = 60.0, db: Session = Depends(get_db)):
    return risk_service.get_high_risk_countries(db, min_score)


@router.get("/countries/{country_code}", response_model=CountryRisk)
def get_country_risk(country_code: str, db: Session = Depends(get_db)):
    risk = risk_service.get_country_risk(db, country_code)
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
