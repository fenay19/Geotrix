from fastapi import Depends, HTTPException, status
from typing import Generator

def get_db() -> Generator:
    try:
        db = "Database Session Placeholder"
        yield db
    finally:
        pass
