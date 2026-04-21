from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.event_model import Event
from ..schemas.event_schema import EventCreate


class EventRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Event]:
        return (
            self.db.query(Event)
            .order_by(Event.timestamp.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_id(self, event_id: int) -> Optional[Event]:
        return self.db.query(Event).filter(Event.id == event_id).first()

    def get_by_country(self, country_id: int) -> List[Event]:
        return (
            self.db.query(Event)
            .filter(Event.country_id == country_id)
            .order_by(Event.timestamp.desc())
            .all()
        )

    def get_top_risks_by_country(self, country_id: int, limit: int = 5) -> List[Event]:
        return (
            self.db.query(Event)
            .filter(Event.country_id == country_id)
            .order_by(Event.severity.desc())
            .limit(limit)
            .all()
        )

    def get_by_type(self, event_type: str) -> List[Event]:
        return (
            self.db.query(Event)
            .filter(Event.event_type == event_type)
            .order_by(Event.timestamp.desc())
            .all()
        )

    def get_high_severity(self, min_severity: int = 7) -> List[Event]:
        return (
            self.db.query(Event)
            .filter(Event.severity >= min_severity)
            .order_by(Event.severity.desc())
            .all()
        )

    def create(self, event_in: EventCreate) -> Event:
        db_event = Event(**event_in.model_dump())
        self.db.add(db_event)
        self.db.commit()
        self.db.refresh(db_event)
        return db_event

    def delete(self, event_id: int) -> bool:
        event = self.get_by_id(event_id)
        if event:
            self.db.delete(event)
            self.db.commit()
            return True
        return False
