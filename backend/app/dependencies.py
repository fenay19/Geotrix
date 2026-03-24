from typing import Generator
from .database.db import SessionLocal


def get_db() -> Generator:
    """Yields a SQLAlchemy database session, ensuring it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
