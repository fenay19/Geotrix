import json
import requests
from typing import Optional
from sqlalchemy.orm import Session
from ..repositories.chat_repo import ChatRepository
from ..repositories.risk_repo import GTIRepository
from ..repositories.event_repo import EventRepository
from ..schemas.chat_schema import ChatSessionCreate, ChatMessageCreate
from ..config import settings


OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


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

    # ── AI  ──────────────────────────────────────────────────────────────────

    def _build_system_context(self, db: Session) -> str:
        """
        Reads live GTI score + top events to build the AI's world-knowledge prompt.
        This acts as a simple RAG (Retrieval-Augmented Generation) context.
        """
        gti_repo = GTIRepository(db)
        event_repo = EventRepository(db)

        gti = gti_repo.get_latest()
        events = event_repo.get_high_severity(min_severity=7)[:5]

        gti_text = f"{gti.current_score} ({gti.severity_category})" if gti else "Unknown"
        event_lines = "\n".join(
            f"- [{e.event_type.upper()}] {e.title} (Severity: {e.severity}/10)"
            for e in events
        ) if events else "- No high-severity events recorded."

        return f"""You are GeoTrade AI — an expert in geopolitical risk analysis and commodity trading.
You help traders understand how global events affect financial markets.

Current Global Tension Index (GTI): {gti_text}

Top Active Geopolitical Risks:
{event_lines}

Always ground your analysis in the above context. Be concise, insightful, and professional.
If asked for trade signals, clearly state they are AI-generated and not financial advice."""

    def get_ai_response(self, db: Session, session_id: int, user_message: str) -> str:
        """
        Full AI response pipeline:
        1. Save user message to DB.
        2. Build system context from live data.
        3. Fetch conversation history for this session.
        4. Call OpenAI API.
        5. Save and return AI response.
        """
        chat_repo = ChatRepository(db)

        # 1. Save user message
        chat_repo.add_message(ChatMessageCreate(
            role="user",
            content=user_message,
            session_id=session_id
        ))

        # 2. Build context
        system_prompt = self._build_system_context(db)

        # 3. Fetch history (last 10 messages for context window)
        history = chat_repo.get_messages(session_id)[-10:]
        openai_messages = [{"role": "system", "content": system_prompt}]
        for msg in history[:-1]:  # Exclude newest user msg we just added — it's the last one
            openai_messages.append({"role": msg.role, "content": msg.content})
        openai_messages.append({"role": "user", "content": user_message})

        ai_reply = self._call_openai(openai_messages)

        # 5. Save AI response
        chat_repo.add_message(ChatMessageCreate(
            role="assistant",
            content=ai_reply,
            session_id=session_id
        ))

        return ai_reply

    def _call_openai(self, messages: list) -> str:
        """Calls OpenAI chat completions API. Falls back gracefully on error."""
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            return "AI service is not configured. Please add OPENAI_API_KEY to your .env file."

        try:
            resp = requests.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 600,
                },
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[ERROR] OpenAI call failed: {e}")
            return "I'm having trouble connecting to the AI service right now. Please try again shortly."


chat_service = ChatService()
