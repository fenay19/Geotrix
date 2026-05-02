from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging
import warnings

_INSECURE_KEY = "placeholder_secret_key"

logger = logging.getLogger("geotrade.config")


class Settings(BaseSettings):
    PROJECT_NAME: str = "geotrade-ai-platform"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    SECRET_KEY: str = _INSECURE_KEY
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DEBUG: bool = True

    # AI/ML API Keys
    OPENAI_API_KEY: Optional[str] = None
    FINNHUB_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        case_sensitive = True


settings = Settings()

# ── Startup safety check ──────────────────────────────────────────────────────
if settings.SECRET_KEY == _INSECURE_KEY:
    msg = (
        "SECURITY WARNING: SECRET_KEY is still the insecure placeholder value. "
        "Set a strong random SECRET_KEY in your .env file "
        "(e.g. `openssl rand -hex 32`). "
        "All JWT tokens can be forged with this key!"
    )
    if not settings.DEBUG:
        raise RuntimeError(msg)   # Hard-fail in production
    warnings.warn(msg, stacklevel=2)
    logger.warning(msg)
