from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from ...schemas.chat_schema import ChatSession, ChatSessionCreate, ChatMessage, ChatMessageCreate
from ...services.chat_service import chat_service
from ...dependencies import get_db, get_current_user
from ...schemas.user_schema import User

router = APIRouter()


# ── Session endpoints ──
@router.get("/sessions", response_model=List[ChatSession])
def get_sessions(user_id: Optional[int] = None, skip: int = 0, limit: int = 20, db: Session = Depends(get_db)):
    return chat_service.get_sessions(db, user_id=user_id, skip=skip, limit=limit)


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


from pydantic import BaseModel

class AskRequest(BaseModel):
    message: str

@router.post("/sessions/{session_id}/ask")
def ask_ai(session_id: int, body: AskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Sends a message, gets an AI response with live geopolitical context."""
    session = chat_service.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Optional check: ensure session belongs to current_user
    if session.user_id and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    reply = chat_service.get_ai_response(db, session_id, body.message)
    return {"session_id": session_id, "reply": reply}
