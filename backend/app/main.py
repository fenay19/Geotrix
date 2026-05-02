from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.logging import setup_logging
from .database.base import Base
from .database.db import engine
from .api.router import api_router
from .ai.embeddings.vector_store import vector_store
from .config import settings

# ── Initialise structured logging before anything else ───────────────────────
logger = setup_logging()

# ── Create DB tables (idempotent) ────────────────────────────────────────────
Base.metadata.create_all(bind=engine)
logger.info("Database tables created/verified.")

# ── Application instance ─────────────────────────────────────────────────────
app = FastAPI(
    title="GeoTrade AI — Geopolitical Trading Intelligence Platform",
    description=(
        "Combines global event monitoring, financial market analysis, "
        "AI-based reasoning, and interactive visualization."
    ),
    version="0.1.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")


# ── Startup event ─────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("GeoTrade Backend starting up...")

    # Warm up the vector store (loads FAISS/numpy index into memory)
    try:
        vector_store.warm_up()
        logger.info("Vector Store warmed up successfully.")
    except Exception as e:
        logger.error("Vector Store warm-up failed: %s", e)

    # Log API key availability (values are never logged)
    logger.info("OpenAI API Key : %s", "Set" if settings.OPENAI_API_KEY else "MISSING")
    logger.info("Finnhub API Key: %s", "Set" if settings.FINNHUB_API_KEY else "MISSING")
    logger.info("News API Key   : %s", "Set" if settings.NEWS_API_KEY else "MISSING")


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
