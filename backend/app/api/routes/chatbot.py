from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ...schemas.chat_schema import ChatSession, ChatSessionCreate, ChatMessage, ChatMessageCreate
from ...services.chat_service import chat_service
from ...dependencies import get_db

router = APIRouter()


# ── Session endpoints ──
@router.get("/sessions", response_model=List[ChatSession])
def get_sessions(skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return chat_service.get_sessions(db, skip=skip, limit=limit)


@router.post("/sessions", response_model=ChatSession, status_code=201)
def create_session(session_in: ChatSessionCreate, db: Session = Depends(get_db)):
    return chat_service.create_session(db, session_in)


@router.get("/sessions/{session_id}", response_model=ChatSession)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = chat_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db)):
    deleted = chat_service.delete_session(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return None


# ── Message endpoints ──
@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessage])
def get_messages(session_id: int, db: Session = Depends(get_db)):
    return chat_service.get_messages(db, session_id)


@router.post("/messages", response_model=ChatMessage, status_code=201)
def add_message(message_in: ChatMessageCreate, db: Session = Depends(get_db)):
    return chat_service.add_message(db, message_in)
