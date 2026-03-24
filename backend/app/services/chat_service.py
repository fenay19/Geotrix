from sqlalchemy.orm import Session
from ..repositories.chat_repo import ChatRepository
from ..schemas.chat_schema import ChatSessionCreate, ChatMessageCreate


class ChatService:
    def get_sessions(self, db: Session, skip: int = 0, limit: int = 20):
        repo = ChatRepository(db)
        return repo.get_all_sessions(skip=skip, limit=limit)

    def get_session(self, db: Session, session_id: int):
        repo = ChatRepository(db)
        return repo.get_session_by_id(session_id)

    def create_session(self, db: Session, session_in: ChatSessionCreate):
        repo = ChatRepository(db)
        return repo.create_session(session_in)

    def delete_session(self, db: Session, session_id: int):
        repo = ChatRepository(db)
        return repo.delete_session(session_id)

    def get_messages(self, db: Session, session_id: int):
        repo = ChatRepository(db)
        return repo.get_messages(session_id)

    def add_message(self, db: Session, message_in: ChatMessageCreate):
        repo = ChatRepository(db)
        return repo.add_message(message_in)


chat_service = ChatService()
