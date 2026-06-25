from pydantic_settings import BaseSettings
from pydantic import model_validator
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DEBUG: bool = True

    # CORS — list of allowed origins (comma-separated in .env).
    # Do NOT use "*" combined with allow_credentials=True (violates CORS spec).
    # Add your production domain here when deploying.
    ALLOWED_ORIGINS: list = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",   # CRA / Next.js dev
        "http://localhost:8080",   # Generic alt port
        "http://127.0.0.1:5173",
    ]

    # AI/ML API Keys and Endpoints
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_AI_MODEL: str = "gpt-4o-mini"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"
    FINNHUB_API_KEY: Optional[str] = None
    NEWS_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None

    # ── ML / Monte Carlo Settings ─────────────────────────────────────────────
    # Confidence threshold below which the LLM backup is triggered (Stage 2)
    ML_CONFIDENCE_THRESHOLD: float = 0.45
    # Directory where trained .pkl model files are persisted
    ML_MODELS_DIR: str = "app/ml/saved_models"
    # Whether to allow yfinance historical data downloads for training
    YFINANCE_ENABLED: bool = True
    # Number of Monte Carlo simulations (higher = more accurate but slower)
    MONTE_CARLO_N_SIMS: int = 10_000

    # ── Background Sync Scheduler Settings ────────────────────────────────────
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_INTERVAL_SECONDS: int = 3600   # Run every 1 hour (was 24h)
    IS_SHUTTING_DOWN: bool = False

    # Hugging Face local cache directory redirection
    HF_HOME: Optional[str] = None

    @model_validator(mode="after")
    def resolve_db_url(self) -> "Settings":
        if self.DATABASE_URL.startswith("sqlite:///"):
            db_path = self.DATABASE_URL[10:]
            clean_path = db_path
            if clean_path.startswith("./"):
                clean_path = clean_path[2:]
            
            if not os.path.isabs(clean_path):
                # Resolve relative to the backend directory (config.py is in backend/app)
                backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                abs_path = os.path.abspath(os.path.join(backend_dir, clean_path))
                formatted_path = abs_path.replace('\\', '/')
                self.DATABASE_URL = f"sqlite:///{formatted_path}"
        return self

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        case_sensitive = True
        extra = "ignore"


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

