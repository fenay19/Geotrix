import requests
import json
from datetime import datetime
from sqlalchemy.orm import Session
from ..services.news_service import news_service
from ..repositories.event_repo import EventRepository
from ..schemas.event_schema import EventCreate
from ..config import settings

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

class NewsPipeline:
    """
    Automated pipeline that fetches global news, uses AI to evaluate its 
    geopolitical severity, and stores high-impact events in the database.
    """

    def sync_geopolitical_events(self, db: Session) -> dict:
        """
        Fetches global news, classifies them via AI, and saves significant events.
        """
        if not settings.NEWS_API_KEY:
            return {"status": "error", "message": "NEWS_API_KEY is not configured."}
            
        if not settings.OPENAI_API_KEY:
            return {"status": "error", "message": "OPENAI_API_KEY is required to classify events."}

        # 1. Fetch raw news
        raw_news = news_service.get_geopolitical_news()
        if not raw_news or "[Demo]" in raw_news[0].get("headline", ""):
            return {"status": "error", "message": "Could not fetch valid news."}

        event_repo = EventRepository(db)
        added_events = 0
        
        # 2. Process each article
        # We only process the top 5 to save API tokens and time during sync
        for article in raw_news[:5]:
            title = article.get("headline", "")
            summary = article.get("summary", "")
            
            # Use AI to evaluate this specific piece of news
            analysis = self._evaluate_news_with_ai(title, summary)
            
            if not analysis:
                continue
                
            # If AI deems it low severity, we ignore it (don't clutter the DB)
            if analysis.get("severity", 0) < 3:
                continue
                
            # Format impact label based on severity
            severity = analysis.get("severity", 5)
            impact_label = "CRITICAL" if severity >= 8 else ("HIGH" if severity >= 6 else "ELEVATED")

            # Create event in DB
            try:
                # We try to extract an ISO datetime, else fallback to now
                ts = datetime.utcnow()
                if article.get("datetime"):
                    try:
                        # Attempt to parse standard ISO 8601 from NewsAPI
                        ts = datetime.fromisoformat(article.get("datetime").replace('Z', '+00:00'))
                    except ValueError:
                        pass
                
                event_in = EventCreate(
                    title=title,
                    description=summary,
                    event_type=analysis.get("event_type", "policy"),
                    severity=severity,
                    impact_label=impact_label,
                    source=article.get("source", "NewsAPI"),
                    timestamp=ts,
                    country_id=None # Optionally we could have AI detect the country code and link it!
                )
                event_repo.create(event_in)
                added_events += 1
            except Exception as e:
                print(f"[ERROR] Failed to save evaluated event: {e}")

        return {
            "status": "success", 
            "articles_processed": len(raw_news[:5]), 
            "events_added": added_events
        }

    def _evaluate_news_with_ai(self, title: str, summary: str) -> dict:
        """
        Asks OpenAI to classify a news snippet for geopolitical impact.
        """
        api_key = settings.OPENAI_API_KEY
        
        prompt = f"""You are a geopolitical risk analyst.
Analyze the following news article and determine its impact on global stability and financial markets.

Title: {title}
Summary: {summary}

Respond ONLY with a valid JSON object matching this schema exactly (no markdown):
{{
  "severity": <integer from 1 to 10, where 10 is global war/catastrophe>,
  "event_type": <string: exactly one of: "war", "sanctions", "economic", "policy", "unrest">,
  "reasoning": "<one short sentence explaining the severity rating>"
}}
"""
        try:
            resp = requests.post(
                OPENAI_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 150,
                },
                timeout=15,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            # Clean up the response to ensure it parses
            content = content.strip().strip("```json").strip("```").strip()
            return json.loads(content)
        except Exception as e:
            print(f"[WARN] AI news evaluation failed: {e}")
            return None


news_pipeline = NewsPipeline()
