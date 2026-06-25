import logging
from typing import Optional
from sqlalchemy.orm import Session

from ..repositories.chat_repo import ChatRepository
from ..repositories.risk_repo import GTIRepository
from ..repositories.event_repo import EventRepository
from ..schemas.chat_schema import ChatSessionCreate, ChatMessageCreate
from ..config import settings
from ..ai.chatbot.chat_engine import get_chat_engine
from ..ai.chatbot.prompt_templates import GEOTRADE_SYSTEM_PROMPT
from ..ai.embeddings.embedding_model import embedding_model
from ..ai.embeddings.vector_store import vector_store

logger = logging.getLogger("geotrade.services.chat")


class ChatService:

    def get_sessions(self, db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 20):
        repo = ChatRepository(db)
        return repo.get_all_sessions(user_id=user_id, skip=skip, limit=limit)

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

    # ── AI (RAG-augmented) ───────────────────────────────────────────────────

    def _build_system_context(self, db: Session, user_message: str) -> str:
        """
        Builds the AI's world-knowledge prompt using a full RAG pipeline:
          1. Embed the user's query and search the vector store for relevant events.
          2. Pull the live GTI score from the DB.
          3. Fall back to DB high-severity events if the vector store is empty.
          4. Merge everything into the system prompt template.
        """
        gti_repo = GTIRepository(db)
        event_repo = EventRepository(db)

        # ── 1. GTI context ───────────────────────────────────────────────
        gti = gti_repo.get_latest()
        gti_text = f"{gti.current_score} ({gti.severity_category})" if gti else "Unknown"

        # ── 2. RAG: embed the user query → search the vector store ───────
        rag_events: list[dict] = []
        try:
            if vector_store.count() > 0:
                query_vec = embedding_model.get_embedding(user_message)
                results = vector_store.search(query_vec, top_k=5, min_score=0.15)
                rag_events = [
                    {
                        "title":      r["metadata"].get("title", "Untitled"),
                        "event_type": r["metadata"].get("event_type", "policy"),
                        "severity":   r["metadata"].get("severity", 5),
                        "score":      r["score"],
                    }
                    for r in results
                ]
                logger.debug(
                    "RAG retrieved %d events for query: '%s'",
                    len(rag_events), user_message[:60],
                )
        except Exception as exc:
            logger.warning("RAG vector search failed, falling back to DB: %s", exc)

        # ── 3. Fallback: top DB events if vector store had nothing ───────
        if rag_events:
            event_lines = "\n".join(
                f"- [{e['event_type'].upper()}] {e['title']} "
                f"(Severity: {e['severity']}/10, Relevance: {e['score']})"
                for e in rag_events
            )
        else:
            db_events = event_repo.get_high_severity(min_severity=7)[:5]
            event_lines = "\n".join(
                f"- [{e.event_type.upper()}] {e.title} (Severity: {e.severity}/10)"
                for e in db_events
            ) if db_events else "- No high-severity events recorded."

        # ── 4. Format the centralized prompt template ────────────────────
        return GEOTRADE_SYSTEM_PROMPT.format(gti=gti_text, events=event_lines)

    def get_ai_response(self, db: Session, session_id: int, user_message: str) -> str:
        """
        Full AI response pipeline:
        1. Save user message to DB.
        2. Build system context from RAG + live data.
        3. Fetch conversation history for this session.
        4. Call OpenAI via ChatEngine.
        5. Save and return AI response.
        """
        chat_repo = ChatRepository(db)

        # 1. Save user message
        chat_repo.add_message(ChatMessageCreate(
            role="user",
            content=user_message,
            session_id=session_id
        ))

        # 2. Build RAG-augmented context (passes user message for embedding)
        system_prompt = self._build_system_context(db, user_message)

        # 3. Fetch history (last 10 messages for context window)
        history = chat_repo.get_messages(session_id)[-10:]
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in history[:-1]:  # Exclude newest user msg we just added — it's the last one
            openai_messages.append({"role": msg.role, "content": msg.content})
        openai_messages.append({"role": "user", "content": user_message})

        # 4. Call OpenAI via the centralized ChatEngine
        ai_reply = self._call_openai(openai_messages)

        # 5. Save AI response
        chat_repo.add_message(ChatMessageCreate(
            role="assistant",
            content=ai_reply,
            session_id=session_id
        ))

        return ai_reply

    def _call_openai(self, messages: list) -> str:
        """Calls OpenAI chat completions via ChatEngine. Falls back gracefully."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return "AI service is not configured. Please add OPENAI_API_KEY to your .env file."

        engine = get_chat_engine(api_key)
        result = engine.get_response(messages, temperature=0.7, max_tokens=600)
        if result is None:
            return "I'm having trouble connecting to the AI service right now. Please try again shortly."
        return result


chat_service = ChatService()
