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
            from ..pipelines.risk_pipeline import risk_pipeline
            
            db = SessionLocal()
            try:
                # ── 1. Geopolitical Events / News (async) ──
                logger.info("Scheduler: Syncing geopolitical events...")
                news_res = await news_pipeline.sync_geopolitical_events(db)
                logger.info("Scheduler: Geopolitical events sync outcome: %s", news_res)
                
                # Helper to run market pipeline sync in executor thread with its own DB session
                def run_market_sync():
                    thread_db = SessionLocal()
                    try:
                        return market_pipeline.sync_all_markets(thread_db)
                    finally:
                        thread_db.close()

                # ── 2. Market Prices & Candle History (blocking/sync API calls) ──
                logger.info("Scheduler: Syncing all market data...")
                loop = asyncio.get_running_loop()
                market_res = await loop.run_in_executor(None, run_market_sync)
                logger.info("Scheduler: Market data sync outcome: %s", market_res)
                
                # Helper to run risk pipeline sync in executor thread with its own DB session
                def run_risk_sync():
                    thread_db = SessionLocal()
                    try:
                        return risk_pipeline.sync_global_risk(thread_db)
                    finally:
                        thread_db.close()

                # ── 3. Synchronise Country Risks and Calculate GTI ──
                logger.info("Scheduler: Synchronising country risks and GTI...")
                risk_res = await loop.run_in_executor(None, run_risk_sync)
                logger.info("Scheduler: Country risks and GTI sync outcome: %s", risk_res)
                
                if risk_res and risk_res.get("status") == "success":
                    new_gti = risk_res.get("new_gti")
                    if new_gti is not None:
                        try:
                            from ..api.routes.ws import manager
                            await manager.broadcast({"type": "gti_update", "score": new_gti})
                            logger.info("Scheduler: Broadcasted new GTI score: %.1f", new_gti)
                        except Exception as ws_exc:
                            logger.error("Scheduler: Failed to broadcast GTI update: %s", ws_exc)
                
            except Exception as e:
                logger.error("Error encountered during background sync execution: %s", e, exc_info=True)
            finally:
                db.close()
                
        except Exception as e:
            logger.error("Unexpected error in background sync scheduler loop: %s", e, exc_info=True)
            
        logger.info("Background sync completed. Waiting %d seconds for the next run...", interval)
        await asyncio.sleep(interval)
