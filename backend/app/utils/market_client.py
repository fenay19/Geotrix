import logging
import requests
from typing import Dict, Any
from ..config import settings

logger = logging.getLogger("geotrade.utils.market_client")


class MarketDataClient:
    """
    Client for interacting with the Finnhub API to fetch real-time and historical market data.
    """
    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self):
        self.api_key = settings.FINNHUB_API_KEY
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not found in settings — market data calls will fail.")

    def _get_params(self, additional_params: Dict[str, Any] = None) -> Dict[str, Any]:
        params = {"token": self.api_key}
        if additional_params:
            params.update(additional_params)
        return params

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches the latest quote for a given symbol.
        Returns a dictionary with: c (current), h (high), l (low), o (open), pc (prev close), t (timestamp)
        """
        url = f"{self.BASE_URL}/quote"
        try:
            response = requests.get(url, params=self._get_params({"symbol": symbol}))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error("Finnhub get_quote failed for %s: %s", symbol, e)
            return {}

    def get_candles(self, symbol: str, category: str, resolution: str, from_ts: int, to_ts: int) -> Dict[str, Any]:
        """
        Fetches historical candles for a given symbol.
        Automatically routes to /stock/candle, /crypto/candle, or /forex/candle based on category.
        """
        # Map category to the specific Finnhub endpoint
        category_lower = category.lower()
        if "crypto" in category_lower:
            endpoint = "/crypto/candle"
        elif "forex" in category_lower or "currency" in category_lower:
            endpoint = "/forex/candle"
        else:
            # Default to stock/index/commodity endpoint
            endpoint = "/stock/candle"

        url = f"{self.BASE_URL}{endpoint}"
        params = self._get_params({
            "symbol": symbol,
            "resolution": resolution,
            "from": from_ts,
            "to": to_ts
        })

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("s") != "ok":
                logger.debug("Finnhub returned no_data or error for %s: %s", symbol, data.get("s"))
                return {}

            return data
        except Exception as e:
            logger.error("Finnhub get_candles failed for %s: %s", symbol, e)
            return {}


market_client = MarketDataClient()
