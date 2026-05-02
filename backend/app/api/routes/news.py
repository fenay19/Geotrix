from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from ...services.news_service import news_service
from ...pipelines.news_pipeline import news_pipeline
from ...dependencies import get_db, require_admin
from ...repositories.event_repo import EventRepository

router = APIRouter()


@router.get("/")
def get_latest_news(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)):
    """
    Returns the latest stored geopolitical events as an intel news feed.
    Used by the Dashboard's intel rail.
    """
    repo = EventRepository(db)
    events = repo.get_all(skip=0, limit=limit)
    return [
        {
            "id":         e.id,
            "title":      e.title,
            "source":     getattr(e, "source", None),
            "event_type": e.event_type,
            "severity":   e.severity,
            "country_id": e.country_id,
            "created_at": str(e.created_at),
        }
        for e in events
    ]



@router.get("/market")
def get_market_news(category: str = "general"):
    """
    Fetches market news from Finnhub.
    Category options: 'general', 'forex', 'crypto', 'merger'
    """
    return news_service.get_market_news(category)


@router.get("/geopolitical")
def get_geopolitical_news():
    """
    Fetches live geopolitical and global tension news from NewsAPI.org.
    """
    return news_service.get_geopolitical_news()


@router.get("/top-stocks")
def get_top_stocks_news(symbols: Optional[str] = None):
    """
    Fetches aggregated company news for top stocks.
    Pass a comma-separated list of symbols via `symbols` (default: AAPL,MSFT,NVDA,AMZN,TSLA).
    """
    symbol_list = ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA"]
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")][:5]
    return news_service.get_top_stocks_news(symbol_list)


@router.get("/company/{symbol}")
def get_company_news(symbol: str, from_date: str, to_date: str):
    """
    Fetches company-specific news from Finnhub.
    Example: GET /news/company/AAPL?from_date=2024-01-01&to_date=2024-01-30
    """
    return news_service.get_company_news(symbol, from_date, to_date)


@router.post("/sync-events")
def sync_global_events(db: Session = Depends(get_db), admin=Depends(require_admin)):
    """
    Triggers the automated news pipeline:
    Fetches real-world global news from NewsAPI, evaluates it with OpenAI, 
    and saves high-severity events to the local database.
    """
    return news_pipeline.sync_geopolitical_events(db)

