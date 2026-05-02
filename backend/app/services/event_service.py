from sqlalchemy.orm import Session
from typing import List, Optional
from ..repositories.event_repo import EventRepository
from ..schemas.event_schema import EventCreate, EventUpdate


class EventService:
    def get_events(self, db: Session, skip: int = 0, limit: int = 100):
        repo = EventRepository(db)
        return repo.get_all(skip=skip, limit=limit)

    def get_event(self, db: Session, event_id: int):
        repo = EventRepository(db)
        return repo.get_by_id(event_id)

    def get_events_by_country(self, db: Session, country_id: int):
        repo = EventRepository(db)
        return repo.get_by_country(country_id)

    def get_top_risks_by_country(self, db: Session, country_id: int, limit: int = 5):
        repo = EventRepository(db)
        return repo.get_top_risks_by_country(country_id, limit)

    def get_events_by_type(self, db: Session, event_type: str):
        repo = EventRepository(db)
        return repo.get_by_type(event_type)

    def get_high_severity_events(self, db: Session, min_severity: int = 7):
        repo = EventRepository(db)
        return repo.get_high_severity(min_severity)

    def create_event(self, db: Session, event_in: EventCreate):
        repo = EventRepository(db)
        return repo.create(event_in)

    def update_event(self, db: Session, event_id: int, event_in: EventUpdate):
        repo = EventRepository(db)
        return repo.update(event_id, event_in.model_dump(exclude_unset=True))

    def delete_event(self, db: Session, event_id: int):
        repo = EventRepository(db)
        return repo.delete(event_id)


event_service = EventService()
