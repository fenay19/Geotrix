import logging
import requests
import xml.etree.ElementTree as ET
from typing import List, Optional
from ..config import settings

logger = logging.getLogger("geotrade.services.news")


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
            logger.warning("NewsService.get_market_news failed: %s", e)
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
            logger.warning("NewsService.get_company_news failed for %s: %s", symbol, e)
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
                    "pageSize": 50,
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
            logger.warning("NewsService.get_geopolitical_news failed: %s", e)
            return self._fallback_news("geopolitical")

    def get_geopolitical_everything(self) -> list:
        """
        Fetches geopolitical news from the 'everything' endpoint using
        targeted keywords. Surfaces sanctions, war, military, energy,
        and cyber events that top-headlines often misses.
        """
        if not settings.NEWS_API_KEY:
            return []
        GEO_QUERY = (
            '("war" OR "conflict" OR "military" OR "sanctions" OR "tariff" OR '
            '"cyberattack" OR "cyber warfare" OR "opec" OR "terrorism" OR "blockade" OR '
            '"airstrike" OR "geopolitical") AND ("China" OR "Taiwan" OR "Russia" OR '
            '"Ukraine" OR "Iran" OR "Israel" OR "North Korea" OR "South Korea" OR '
            '"NATO" OR "Red Sea" OR "Strait of Hormuz")'
        )
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q":        GEO_QUERY,
                    "language": "en",
                    "pageSize": 100,
                    "sortBy":   "publishedAt",
                    "apiKey":   settings.NEWS_API_KEY,
                },
                timeout=12,
            )
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])
            return [
                {
                    "headline": a.get("title"),
                    "summary":  a.get("description") or a.get("content", "")[:300],
                    "source":   a.get("source", {}).get("name", "NewsAPI"),
                    "url":      a.get("url"),
                    "datetime": a.get("publishedAt"),
                    "category": "geopolitical",
                    "image":    a.get("urlToImage"),
                }
                for a in articles
                if a.get("title") and "[Removed]" not in (a.get("title") or "")
            ]
        except Exception as e:
            logger.warning("NewsService.get_geopolitical_everything failed: %s", e)
            return []

    def get_gdelt_events(self, max_records: int = 25) -> list:
        """
        Fetches geopolitical events from the GDELT Project Doc API.
        GDELT is 100% free, updated every 15 minutes, and requires no API key.
        Rate-limit: maximum 1 request per 5 seconds. Returns [] on 429 or failure.
        """
        query = (
            '("sanctions" OR "military" OR "ceasefire" OR "cyberattack" OR '
            '"diplomatic summit" OR "trade tariff" OR "energy security" OR "oil embargo")'
        )
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": max_records,
            "format": "json"
        }
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            resp = requests.get(url, params=params, headers=headers, timeout=5)
            if resp.status_code == 429:
                logger.warning("GDELT API returned 429 (Too Many Requests). Skipping GDELT for this sync run.")
                return []
            resp.raise_for_status()
            data = resp.json()
            articles = data.get("articles", [])
            
            normalized = []
            for a in articles:
                title = (a.get("title") or "").strip()
                url_str = (a.get("url") or "").strip()
                pub_date = a.get("seendate")
                
                if not title or not url_str:
                    continue
                
                if "[Removed]" in title or "Page Not Found" in title:
                    continue
                
                domain = a.get("domain") or "GDELT"
                
                date_str = None
                if pub_date and len(pub_date) >= 15:
                    try:
                        date_str = f"{pub_date[0:4]}-{pub_date[4:6]}-{pub_date[6:8]}T{pub_date[9:11]}:{pub_date[11:13]}:{pub_date[13:15]}Z"
                    except Exception:
                        pass
                
                if not date_str:
                    from datetime import datetime, timezone
                    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

                normalized.append({
                    "headline": title,
                    "summary": f"Geopolitical event reported by {domain}. Article URL: {url_str}",
                    "source": domain,
                    "url": url_str,
                    "datetime": date_str,
                    "category": "geopolitical",
                    "image": None,
                    "is_gdelt": True
                })
            return normalized
        except Exception as e:
            logger.warning("NewsService.get_gdelt_events failed: %s", e)
            return []

    def parse_rss_feed(self, url: str, source_name: str) -> list:
        """
        Fetches and parses an RSS feed XML.
        Uses Python's native xml.etree.ElementTree (no external dependencies).
        """
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            
            root = ET.fromstring(resp.content)
            
            articles = []
            for item in root.findall(".//item"):
                title = item.findtext("title")
                summary = item.findtext("description")
                link = item.findtext("link")
                pub_date = item.findtext("pubDate")
                
                if not title:
                    continue
                
                clean_summary = ""
                if summary:
                    import re
                    clean_summary = re.sub(r'<[^>]*>', '', summary)
                    clean_summary = clean_summary.strip()
                
                articles.append({
                    "headline": title.strip(),
                    "summary": clean_summary or f"News update from {source_name}.",
                    "source": source_name,
                    "url": (link or "").strip(),
                    "datetime": pub_date,
                    "category": "geopolitical",
                    "image": None,
                })
            return articles
        except Exception as e:
            logger.warning("NewsService: failed to parse RSS feed %s (%s): %s", source_name, url, e)
            return []

    def get_bbc_news(self) -> list:
        """Fetches latest world news articles from BBC RSS."""
        return self.parse_rss_feed("http://feeds.bbci.co.uk/news/world/rss.xml", "BBC News")

    def get_aljazeera_news(self) -> list:
        """Fetches latest world news articles from Al Jazeera RSS."""
        return self.parse_rss_feed("https://www.aljazeera.com/xml/rss/all.xml", "Al Jazeera")

    def get_reuters_news(self) -> list:
        """Fetches latest Reuters articles using Google News RSS search query."""
        url = "https://news.google.com/rss/search?q=source:Reuters&hl=en-US&gl=US&ceid=US:en"
        return self.parse_rss_feed(url, "Reuters")

    def _fallback_news(self, category: str, custom_message: str = "") -> list:
        msg = custom_message or "Add FINNHUB_API_KEY to your .env file to enable real-time news."
        return [
            {
                "headline": f"[Demo] Live {category.upper()} news requires an API key.",
                "summary":  msg,
                "source":   "GeoTrade AI",
                "url":      None,
                "datetime": None,
                "category": category,
                "image":    None,
            }
        ]

    def get_top_stocks_news(self, symbols: List[str]) -> List[dict]:
        """
        Fetches company-specific news for the given symbols, aggregates, and sorts them by date.
        """
        import datetime
        to_date = datetime.date.today().strftime("%Y-%m-%d")
        from_date = (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        all_news = []
        for symbol in symbols:
            news = self.get_company_news(symbol, from_date, to_date)
            # Add symbol flag to each article
            for article in news:
                if "[Demo]" not in article.get("headline", ""):
                    article["symbol"] = symbol
                    all_news.append(article)
                    
        # If no real news was fetched, return demo placeholders for the requested symbols
        if not all_news:
            for symbol in symbols:
                all_news.append({
                    "headline": f"[Demo] Live news for {symbol} requires a Finnhub API key.",
                    "summary": "Add FINNHUB_API_KEY to your .env file to enable real-time company news.",
                    "source": "GeoTrade AI",
                    "url": None,
                    "datetime": int(datetime.datetime.now().timestamp()),
                    "category": symbol,
                    "image": None,
                    "symbol": symbol
                })
            return all_news

        # Sort by datetime (epoch seconds) descending
        all_news.sort(key=lambda x: x.get("datetime") or 0, reverse=True)
        return all_news[:25]


news_service = NewsService()

