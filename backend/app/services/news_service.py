import requests
from typing import List, Optional
from ..config import settings


class NewsService:
    """
    Service for fetching market and geopolitical news from Finnhub.
    Falls back gracefully if the API key is missing.
    """
    BASE_URL = "https://finnhub.io/api/v1"
    NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"


    def _get_headers(self) -> dict:
        return {"X-Finnhub-Token": settings.FINNHUB_API_KEY or ""}

    def get_market_news(self, category: str = "general") -> List[dict]:
        """
        Fetches general market news.
        Category options: 'general', 'forex', 'crypto', 'merger'
        """
        if not settings.FINNHUB_API_KEY:
            return self._fallback_news("market")

        try:
            resp = requests.get(
                f"{self.BASE_URL}/news",
                params={"category": category},
                headers=self._get_headers(),
                timeout=10,
            )
            resp.raise_for_status()
            articles = resp.json()
            # Normalize to a consistent shape
            return [
                {
                    "headline": a.get("headline"),
                    "summary": a.get("summary"),
                    "source": a.get("source"),
                    "url": a.get("url"),
                    "datetime": a.get("datetime"),
                    "category": category,
                    "image": a.get("image"),
                }
                for a in articles[:20]  # Cap at 20 articles
            ]
        except Exception as e:
            print(f"[ERROR] NewsService.get_market_news failed: {e}")
            return self._fallback_news("market")

    def get_company_news(self, symbol: str, from_date: str, to_date: str) -> List[dict]:
        """
        Fetches company-specific news from Finnhub.
        Dates format: 'YYYY-MM-DD'
        """
        if not settings.FINNHUB_API_KEY:
            return self._fallback_news(symbol)

        try:
            resp = requests.get(
                f"{self.BASE_URL}/company-news",
                params={"symbol": symbol, "from": from_date, "to": to_date},
                headers=self._get_headers(),
                timeout=10,
            )
            resp.raise_for_status()
            articles = resp.json()
            return [
                {
                    "headline": a.get("headline"),
                    "summary": a.get("summary"),
                    "source": a.get("source"),
                    "url": a.get("url"),
                    "datetime": a.get("datetime"),
                    "category": symbol,
                    "image": a.get("image"),
                }
                for a in articles[:15]
            ]
        except Exception as e:
            print(f"[ERROR] NewsService.get_company_news failed for {symbol}: {e}")
            return self._fallback_news(symbol)

    def get_geopolitical_news(self) -> List[dict]:
        """
        Fetches geopolitical and global tension news from NewsAPI.org.
        Focuses on categories and keywords relevant to global risk.
        """
        if not settings.NEWS_API_KEY:
            return self._fallback_news("geopolitical", "Add NEWS_API_KEY to your .env file to enable global tension news.")

        try:
            # We use 'general' category but could refine with specific queries or breaking news sources
            resp = requests.get(
                f"{self.NEWSAPI_URL}",
                params={
                    "category": "general",
                    "language": "en",
                    "pageSize": 15,
                    "apiKey": settings.NEWS_API_KEY
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])
            
            return [
                {
                    "headline": a.get("title"),
                    "summary": a.get("description"),
                    "source": a.get("source", {}).get("name", "Unknown Source"),
                    "url": a.get("url"),
                    "datetime": a.get("publishedAt"),
                    "category": "geopolitical",
                    "image": a.get("urlToImage"),
                }
                for a in articles if a.get("title") and a.get("description")
            ]
        except Exception as e:
            print(f"[ERROR] NewsService.get_geopolitical_news failed: {e}")
            return self._fallback_news("geopolitical")

    def _fallback_news(self, category: str, custom_message: str = None) -> List[dict]:

        """Returns informative placeholder items when the API is unavailable."""
        msg = custom_message or "Add FINNHUB_API_KEY to your .env file to enable real-time news."
        return [
            {
                "headline": f"[Demo] Live {category.upper()} news requires an API key.",
                "summary": msg,
                "source": "GeoTrade AI",                "url": None,
                "datetime": None,
                "category": category,
                "image": None,
            }
        ]


news_service = NewsService()
