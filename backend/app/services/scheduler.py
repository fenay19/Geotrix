import asyncio
import logging
from ..config import settings

logger = logging.getLogger("geotrade.services.scheduler")

async def background_sync_scheduler():
    """
    Background job runner that periodically synchronises geopolitical events/news,
    market data (live quotes and historical candles), and recalculates the GTI index.
    Runs concurrently inside FastAPI's asyncio event loop.
    """
    # Wait briefly on startup before first execution
    await asyncio.sleep(10)
    
    interval = settings.SCHEDULER_INTERVAL_SECONDS
    logger.info("Background sync scheduler started. Interval: %d seconds.", interval)
    
    while True:
        try:
            logger.info("Executing scheduled background sync (News, Prices, GTI)...")
            from ..database.db import SessionLocal
            from ..pipelines.news_pipeline import news_pipeline
            from ..pipelines.market_pipeline import market_pipeline
            from .gti_service import gti_service
            
            db = SessionLocal()
            try:
                # ── 1. Geopolitical Events / News (async) ──
                logger.info("Scheduler: Syncing geopolitical events...")
                news_res = await news_pipeline.sync_geopolitical_events(db)
                logger.info("Scheduler: Geopolitical events sync outcome: %s", news_res)
                
                # ── 2. Market Prices & Candle History (blocking/sync API calls) ──
                logger.info("Scheduler: Syncing all market data...")
                loop = asyncio.get_running_loop()
                market_res = await loop.run_in_executor(None, market_pipeline.sync_all_markets, db)
                logger.info("Scheduler: Market data sync outcome: %s", market_res)
                
                # ── 3. Calculate Global Tension Index (GTI) ──
                logger.info("Scheduler: Recalculating Global Tension Index (GTI)...")
                gti_score = await loop.run_in_executor(None, gti_service.calculate_current_gti, db)
                logger.info("Scheduler: Calculated GTI score: %s", gti_score)
                
            except Exception as e:
                logger.error("Error encountered during background sync execution: %s", e, exc_info=True)
            finally:
                db.close()
                
        except Exception as e:
            logger.error("Unexpected error in background sync scheduler loop: %s", e, exc_info=True)
            
        logger.info("Background sync completed. Waiting %d seconds for the next run...", interval)
        await asyncio.sleep(interval)
