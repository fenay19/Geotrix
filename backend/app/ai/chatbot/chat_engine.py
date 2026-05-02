"""
Central abstraction for all OpenAI LLM calls in GeoTrade AI.

All services (chat, signals, simulation) and pipelines (news, risk) should
call this engine instead of making raw requests.post() calls themselves.

Benefits:
  - Single place to swap models (gpt-4o-mini → gpt-4o, etc.)
  - Consistent error handling and logging
  - Easy to mock in unit tests
  - Token usage can be tracked here later
"""

import logging
from typing import Optional

from ...utils.api_clients import api_client
from ...utils.helpers import parse_json_response
from ...core.constants import DEFAULT_AI_MODEL, OPENAI_API_URL

logger = logging.getLogger("geotrade.chat_engine")


class ChatEngine:
    """
    Thin wrapper around the OpenAI Chat Completions API.
    Provides get_response() for plain text and get_json_response() for structured output.
    """

    def __init__(self, api_key: str, model: str = DEFAULT_AI_MODEL):
        self.api_key = api_key
        self.model = model

    def _build_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_response(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 600,
        timeout: int = 30,
    ) -> Optional[str]:
        """
        Calls Chat Completions and returns the assistant's raw text reply.
        Returns None on any error so callers can fall back gracefully.
        """
        if not self.api_key:
            logger.warning("ChatEngine: OPENAI_API_KEY is not configured.")
            return None
        try:
            data = api_client.post_data(
                OPENAI_API_URL,
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                headers=self._build_headers(),
                timeout=timeout,
            )
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            logger.error("ChatEngine.get_response failed: %s", exc)
            return None

    def get_json_response(
        self,
        messages: list,
        temperature: float = 0.3,
        max_tokens: int = 600,
        timeout: int = 30,
    ) -> Optional[dict]:
        """
        Calls the API, strips markdown fences, and parses the result as JSON.
        Returns None on failure so callers can use a rule-based fallback.
        """
        raw = self.get_response(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        if raw is None:
            return None
        result = parse_json_response(raw)
        if result is None:
            logger.warning("ChatEngine: could not parse JSON: %s", raw[:200])
        return result

    def ask(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 600,
        timeout: int = 30,
    ) -> Optional[str]:
        """Convenience: single user prompt with optional system message → plain text."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.get_response(messages, temperature=temperature, max_tokens=max_tokens, timeout=timeout)

    def ask_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 600,
        timeout: int = 30,
    ) -> Optional[dict]:
        """Convenience: single user prompt → parsed JSON dict."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.get_json_response(messages, temperature=temperature, max_tokens=max_tokens, timeout=timeout)


def get_chat_engine(api_key: str, model: str = DEFAULT_AI_MODEL) -> ChatEngine:
    """Factory: creates a ChatEngine with the given credentials."""
    return ChatEngine(api_key=api_key, model=model)
