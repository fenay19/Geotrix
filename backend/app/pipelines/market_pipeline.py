from sqlalchemy.orm import Session
from ..services.market_service import market_service
from ..services.market_data_service import market_data_service


class MarketPipeline:
    """
    Orchestration pipeline that syncs financial market data from Finnhub
    into the local database. Iterates all registered markets, updates
    live quotes and fetches historical OHLC candles.
    """

    def sync_all_markets(self, db: Session, history_days: int = 30) -> dict:
        """
        Syncs live prices and historical candle data for every market in the DB.

        Args:
            db:             SQLAlchemy session.
            history_days:  How many days of historical candles to fetch (default 30).

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

        for market in markets:
            symbol = market.symbol

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
