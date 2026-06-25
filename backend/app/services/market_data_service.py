from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
import time
from ..utils.market_client import market_client
from ..repositories.market_repo import MarketRepository
from ..schemas.market_schema import MarketHistoryCreate
from ..models.market_model import MarketHistory

logger = logging.getLogger("geotrade.services.market_data")


class MarketDataService:
    """
    Service to handle synchronization of market data from external APIs to the local database.
    """

    def sync_live_price(self, db: Session, symbol: str) -> bool:
        """
        Fetches the latest price from Finnhub and updates the Market record.
        """
        repo = MarketRepository(db)
        market = repo.get_by_symbol(symbol)
        if not market:
            logger.debug("Market not found for symbol: %s", symbol)
            return False

        quote = market_client.get_quote(symbol)
        if not quote or "c" not in quote:
            return False

        repo.update_price(symbol, quote["c"])
        return True

    def sync_historical_candles(self, db: Session, symbol: str, days: int = 180) -> int:
        """
        Fetches historical OHLC data and populates the MarketHistory table.
        Skips rows that already exist for the same (market_id, timestamp) to prevent duplicates.
        """
        repo = MarketRepository(db)
        market = repo.get_by_symbol(symbol)
        if not market:
            return 0

        # Calculate time range
        to_ts = int(time.time())
        from_ts = int((datetime.now() - timedelta(days=days)).timestamp())

        # Fetch from client
        data = market_client.get_candles(
            symbol=symbol,
            category=market.category,
            resolution="D",  # Daily resolution
            from_ts=from_ts,
            to_ts=to_ts
        )

        if not data or "c" not in data:
            return 0

        # Build a set of existing timestamps for this market to skip duplicates
        existing_ts = {
            row.timestamp
            for row in db.query(MarketHistory.timestamp)
            .filter(MarketHistory.market_id == market.id)
            .all()
        }

        count = 0
        for i in range(len(data["c"])):
            candle_dt = datetime.fromtimestamp(data["t"][i])
            if candle_dt in existing_ts:
                continue   # skip duplicate

            db_history = MarketHistory(
                market_id=market.id,
                open=data["o"][i],
                high=data["h"][i],
                low=data["l"][i],
                close=data["c"][i],
                volume=data["v"][i] if "v" in data else 0,
                timestamp=candle_dt,
            )
            db.add(db_history)
            count += 1

        if count > 0:
            db.commit()

        logger.debug("Inserted %d new candles for %s (skipped duplicates).", count, symbol)
        return count


market_data_service = MarketDataService()
