from sqlalchemy.orm import Session
import logging
from ..services.market_service import market_service
from ..services.market_data_service import market_data_service
from ..config import settings

logger = logging.getLogger("geotrade.pipelines.market")


class MarketPipeline:
    """
    Orchestration pipeline that syncs financial market data from Finnhub
    into the local database. Iterates all registered markets, updates
    live quotes and fetches historical OHLC candles.
    """

    def sync_all_markets(self, db: Session, history_days: int = 180) -> dict:
        """
        Syncs live prices and historical candle data for every market in the DB.

        Args:
            db:             SQLAlchemy session.
            history_days:  How many days of historical candles to fetch (default 180).

        Returns:
            Summary dict with counts of updated prices and inserted candles.
        """
        markets = market_service.get_markets(db)

        if not markets:
            return {
                "status": "warning",
                "message": "No markets found in the database. Seed the DB first.",
                "prices_updated": 0,
                "candles_inserted": 0,
            }

        prices_updated = 0
        candles_inserted = 0
        errors = []

        import re
        VALID_SYMBOL_PATTERN = re.compile(r'^[A-Z0-9^=\-\._]{1,15}$')

        for market in markets:
            if settings.IS_SHUTTING_DOWN:
                logger.info("Application shutdown detected. Stopping market data sync.")
                break
            symbol = market.symbol

            # Validate symbol to avoid fetching garbage (e.g., placeholder "STRING")
            if not symbol or not VALID_SYMBOL_PATTERN.match(symbol.upper()):
                logger.warning("Skipping invalid market symbol: %r", symbol)
                continue

            # ── 1. Sync live price ──────────────────────────────────────────
            try:
                ok = market_data_service.sync_live_price(db, symbol)
                if ok:
                    prices_updated += 1
                else:
                    errors.append(f"[{symbol}] Could not fetch live price (Finnhub returned empty).")
            except Exception as e:
                errors.append(f"[{symbol}] Live price error: {e}")

            # ── 2. Sync historical candles ──────────────────────────────────
            try:
                inserted = market_data_service.sync_historical_candles(db, symbol, days=history_days)
                candles_inserted += inserted
            except Exception as e:
                errors.append(f"[{symbol}] Historical candle error: {e}")

        return {
            "status": "success" if not errors else "partial",
            "markets_processed": len(markets),
            "prices_updated": prices_updated,
            "candles_inserted": candles_inserted,
            "errors": errors,
        }


market_pipeline = MarketPipeline()
