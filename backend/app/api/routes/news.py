from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ...services.news_service import news_service
from ...pipelines.news_pipeline import news_pipeline
from ...dependencies import get_db

router = APIRouter()


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


@router.get("/company/{symbol}")
def get_company_news(symbol: str, from_date: str, to_date: str):
    """
    Fetches company-specific news from Finnhub.
    Example: GET /news/company/AAPL?from_date=2024-01-01&to_date=2024-01-30
    """
    return news_service.get_company_news(symbol, from_date, to_date)


@router.post("/sync-events")
def sync_global_events(db: Session = Depends(get_db)):
    """
    Triggers the automated news pipeline:
    Fetches real-world global news from NewsAPI, evaluates it with OpenAI, 
    and saves high-severity events to the local database.
    """
    return news_pipeline.sync_geopolitical_events(db)
