from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.event_schema import Event, EventCreate, EventUpdate
from ...services.event_service import event_service
from ...dependencies import get_db

router = APIRouter()


@router.get("/", response_model=List[Event])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return event_service.get_events(db, skip=skip, limit=limit)


@router.post("/", response_model=Event, status_code=201)
def create_event(event_in: EventCreate, db: Session = Depends(get_db)):
    return event_service.create_event(db, event_in)


@router.get("/high-severity", response_model=List[Event])
def get_high_severity_events(
    min_severity: int = 7, db: Session = Depends(get_db)
):
    return event_service.get_high_severity_events(db, min_severity)


@router.get("/type/{event_type}", response_model=List[Event])
def get_events_by_type(event_type: str, db: Session = Depends(get_db)):
    return event_service.get_events_by_type(db, event_type)


@router.get("/country/{country_id}", response_model=List[Event])
def get_events_by_country(country_id: int, db: Session = Depends(get_db)):
    return event_service.get_events_by_country(db, country_id)


@router.get("/top-risks/{country_id}", response_model=List[Event])
def get_top_risks_by_country(country_id: int, limit: int = 5, db: Session = Depends(get_db)):
    return event_service.get_top_risks_by_country(db, country_id, limit)


@router.get("/{event_id}", response_model=Event)
def read_event(event_id: int, db: Session = Depends(get_db)):
    event = event_service.get_event(db, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=Event)
def update_event(event_id: int, event_in: EventUpdate, db: Session = Depends(get_db)):
    event = event_service.update_event(db, event_id, event_in)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    deleted = event_service.delete_event(db, event_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Event not found")
    return None
