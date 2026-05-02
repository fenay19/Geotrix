from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..config import settings

# check_same_thread=False is required for SQLite with FastAPI's multi-threaded request handling
_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
