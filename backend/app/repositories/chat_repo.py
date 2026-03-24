from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.chat_model import ChatSession, ChatMessage
from ..schemas.chat_schema import ChatSessionCreate, ChatMessageCreate


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Session methods ──
    def get_all_sessions(self, skip: int = 0, limit: int = 20) -> List[ChatSession]:
        return (
            self.db.query(ChatSession)
            .order_by(ChatSession.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_session_by_id(self, session_id: int) -> Optional[ChatSession]:
        return (
            self.db.query(ChatSession)
            .filter(ChatSession.id == session_id)
            .first()
        )

    def create_session(self, session_in: ChatSessionCreate) -> ChatSession:
        db_session = ChatSession(**session_in.model_dump())
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session

    def delete_session(self, session_id: int) -> bool:
        session = self.get_session_by_id(session_id)
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False

    # ── Message methods ──
    def get_messages(self, session_id: int) -> List[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.timestamp.asc())
            .all()
        )

    def add_message(self, message_in: ChatMessageCreate) -> ChatMessage:
        db_msg = ChatMessage(**message_in.model_dump())
        self.db.add(db_msg)
        self.db.commit()
        self.db.refresh(db_msg)
        return db_msg
