"""
Volatility model: computes historical volatility and ATR from price series.
These values feed into the TradingSignal model's atr and volatility_level fields
which were previously always left as None / "Medium".
"""

import logging
import math
from typing import Optional

logger = logging.getLogger("geotrade.forecasting.volatility")


class VolatilityModel:
    """
    Computes annualized historical volatility (HV) and Average True Range (ATR).
    All methods are pure Python/math — no external dependencies required.
    """

    def estimate_volatility(self, returns: list) -> float:
        """
        Computes annualized historical volatility from a list of price returns
        (not log-returns; e.g. [0.01, -0.02, ...]).

        Args:
            returns: list of period returns as decimals

        Returns:
            Annualized volatility as a float (e.g. 0.18 = 18%)
        """
        if len(returns) < 2:
            return 0.15  # sensible default

        n = len(returns)
        mean = sum(returns) / n
        variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
        std = math.sqrt(variance)
        # Annualize: multiply by sqrt(252) trading days
        return round(std * math.sqrt(252), 4)

    def get_atr(
        self,
        highs: list,
        lows: list,
        closes: list,
        period: int = 14,
    ) -> float:
        """
        Computes Average True Range (ATR) — used to set stop_loss distances.

        Args:
            highs:  list of period high prices
            lows:   list of period low prices
            closes: list of period close prices
            period: ATR smoothing period (default 14)

        Returns:
            ATR value as a float
        """
        if len(highs) < 2:
            return 0.0

        true_ranges = []
        for i in range(1, len(highs)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i - 1])
            lc = abs(lows[i] - closes[i - 1])
            true_ranges.append(max(hl, hc, lc))

        if not true_ranges:
            return 0.0

        # Simple moving average of True Range over the period
        relevant = true_ranges[-period:]
        return round(sum(relevant) / len(relevant), 4)

    def classify_volatility(self, annualized_vol: float) -> str:
        """
        Maps annualized volatility to a human-readable label.
        Returns "Low", "Medium", or "High".
        """
        if annualized_vol < 0.12:
            return "Low"
        if annualized_vol < 0.25:
            return "Medium"
        return "High"

    def compute_from_ohlc(self, candles: list) -> dict:
        """
        Convenience: compute all volatility metrics from a list of OHLC candle dicts.

        Args:
            candles: list of dicts with keys: open, high, low, close

        Returns:
            {
                "annualized_vol": float,
                "volatility_label": str,
                "atr": float
            }
        """
        if len(candles) < 2:
            return {"annualized_vol": 0.15, "volatility_label": "Medium", "atr": 0.0}

        closes = [c["close"] for c in candles]
        highs  = [c["high"]  for c in candles]
        lows   = [c["low"]   for c in candles]

        # Compute daily returns
        returns = [
            (closes[i] - closes[i - 1]) / closes[i - 1]
            for i in range(1, len(closes))
            if closes[i - 1] != 0
        ]

        vol = self.estimate_volatility(returns)
        atr = self.get_atr(highs, lows, closes)

        return {
            "annualized_vol":   vol,
            "volatility_label": self.classify_volatility(vol),
            "atr":              atr,
        }


volatility_model = VolatilityModel()
