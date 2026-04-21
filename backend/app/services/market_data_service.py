from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import time
from ..utils.market_client import market_client
from ..repositories.market_repo import MarketRepository
from ..schemas.market_schema import MarketHistoryCreate

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
            print(f"[DEBUG] Market not found for symbol: {symbol}")
            return False

        quote = market_client.get_quote(symbol)
        if not quote or "c" not in quote:
            return False

        repo.update_price(symbol, quote["c"])
        return True

    def sync_historical_candles(self, db: Session, symbol: str, days: int = 30) -> int:
        """
        Fetches historical OHLC data and populates the MarketHistory table.
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

        # Parse Finnhub response (lists of values)
        count = 0
        for i in range(len(data["c"])):
            history_in = MarketHistoryCreate(
                market_id=market.id,
                open=data["o"][i],
                high=data["h"][i],
                low=data["l"][i],
                close=data["c"][i],
                volume=data["v"][i] if "v" in data else 0,
                timestamp=datetime.fromtimestamp(data["t"][i])
            )
            repo.add_history(history_in)
            count += 1

        return count

market_data_service = MarketDataService()
