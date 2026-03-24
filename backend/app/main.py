from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.router import api_router
from .database.base import Base
from .database.db import engine

# Create all tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GeoTrade AI — Geopolitical Trading Intelligence Platform",
    description="Combines global event monitoring, financial market analysis, AI-based reasoning, and interactive visualization.",
    version="0.1.0",
)

# CORS — allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
