import logging
from typing import Dict, Any
import yfinance as yf
from datetime import datetime

logger = logging.getLogger("geotrade.utils.market_client")


class MarketDataClient:
    """
    Client for interacting with Yahoo Finance (yfinance) to fetch real-time
    and historical market data. 100% free, requiring no API keys.
    """

    TICKER_MAP = {
        "GOLD":      "GC=F",
        "OIL_BRENT": "BZ=F",
        "SP500":     "^GSPC",
        "XAUUSD":    "GC=F",
        "BTCUSD":    "BTC-USD",
        "WTI":       "CL=F",
        "HSI":       "^HSI",
        "LMT":       "LMT",
        "INDA":      "INDA",
    }

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Fetches the latest quote for a given symbol using Yahoo Finance.
        Returns a dictionary with: c (current), h (high), l (low), o (open), pc (prev close), t (timestamp)
        """
        yf_ticker = self.TICKER_MAP.get(symbol, symbol)
        try:
            ticker = yf.Ticker(yf_ticker)
            # Fetch last 5 days of history to get current and previous close
            df = ticker.history(period="5d", interval="1d")
            if not df.empty:
                df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
                
                last_row = df.iloc[-1]
                prev_close = float(df["close"].iloc[-2]) if len(df) >= 2 else float(last_row["close"])
                
                return {
                    "c": float(last_row["close"]),
                    "h": float(last_row["high"]),
                    "l": float(last_row["low"]),
                    "o": float(last_row["open"]),
                    "pc": prev_close,
                    "t": int(df.index[-1].timestamp()),
                }
            else:
                logger.warning("yfinance returned empty quote history for %s", yf_ticker)
        except Exception as e:
            logger.error("yfinance get_quote failed for %s (mapped: %s): %s", symbol, yf_ticker, e)
            
        return {}

    def get_candles(self, symbol: str, category: str, resolution: str, from_ts: int, to_ts: int) -> Dict[str, Any]:
        """
        Fetches historical candles for a given symbol using Yahoo Finance.
        """
        yf_ticker = self.TICKER_MAP.get(symbol, symbol)
        try:
            start_date = datetime.fromtimestamp(from_ts).strftime("%Y-%m-%d")
            end_date = datetime.fromtimestamp(to_ts).strftime("%Y-%m-%d")
            
            logger.info("yfinance fetching history for %s (mapped: %s) from %s to %s", symbol, yf_ticker, start_date, end_date)
            df = yf.download(yf_ticker, start=start_date, end=end_date, interval="1d", progress=False)
            
            if not df.empty:
                df.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in df.columns]
                timestamps = [int(t.timestamp()) for t in df.index]
                
                return {
                    "s": "ok",
                    "o": [float(x) for x in df["open"]],
                    "h": [float(x) for x in df["high"]],
                    "l": [float(x) for x in df["low"]],
                    "c": [float(x) for x in df["close"]],
                    "v": [float(x) for x in df["volume"]],
                    "t": timestamps
                }
            else:
                logger.warning("yfinance returned empty dataframe for %s", yf_ticker)
        except Exception as yfe:
            logger.error("yfinance get_candles failed for %s (mapped: %s): %s", symbol, yf_ticker, yfe)

        return {}


market_client = MarketDataClient()
