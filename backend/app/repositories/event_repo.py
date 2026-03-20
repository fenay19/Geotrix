from sqlalchemy.orm import Session
from ..models.event_model import Event

class EventRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self):
        return self.db.query(Event).all()
