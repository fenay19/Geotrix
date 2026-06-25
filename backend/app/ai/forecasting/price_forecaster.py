"""
Price forecaster: predicts future asset prices using historical OHLC data
and geopolitical context.

Strategy:
  1. PRIMARY: OpenAI GPT-4o-mini with price history + GTI context.
  2. FALLBACK: Simple linear trend extrapolation from recent closes.
"""

import logging
from typing import Optional

from ...utils.api_clients import api_client
from ...utils.helpers import parse_json_response
from ...core.constants import DEFAULT_AI_MODEL, OPENAI_API_URL
from ..chatbot.prompt_templates import PRICE_FORECAST_PROMPT

logger = logging.getLogger("geotrade.forecasting.price")


class PriceForecaster:
    """
    Generates a price forecast for a financial asset over a given horizon.
    Returns structured data suitable for the /markets/{symbol}/forecast endpoint.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def forecast(
        self,
        symbol: str,
        horizon: int,
        history: Optional[list] = None,
        gti_score: float = 50.0,
    ) -> dict:
        """
        Args:
            symbol:    Asset ticker (e.g. "GOLD", "AAPL")
            horizon:   Number of trading days to forecast
            history:   List of close prices (oldest → newest), or list of OHLC dicts
            gti_score: Current GTI score for geopolitical context

        Returns:
            {
                "symbol":        str,
                "horizon_days":  int,
                "forecast":      list[float],
                "lower_bound":   list[float],
                "upper_bound":   list[float],
                "trend":         "UP" | "DOWN" | "SIDEWAYS",
                "confidence":    float,
                "reasoning":     str
            }
        """
        closes = self._extract_closes(history or [])

        if self.api_key and len(closes) >= 5:
            result = self._openai_forecast(symbol, horizon, closes, gti_score)
            if result:
                return result

        return self._linear_forecast(symbol, horizon, closes)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _extract_closes(self, history: list) -> list:
        """Handles both list[float] and list[dict with 'close' key]."""
        if not history:
            return []
        if isinstance(history[0], dict):
            return [c["close"] for c in history if "close" in c]
        return [float(p) for p in history]

    def _openai_forecast(
        self, symbol: str, horizon: int, closes: list, gti_score: float
    ) -> Optional[dict]:
        recent = closes[-20:]  # last 20 closes
        price_str = ", ".join(f"{p:.2f}" for p in recent)
        prompt = PRICE_FORECAST_PROMPT.format(
            symbol=symbol,
            horizon=horizon,
            prices=price_str,
            gti_score=round(gti_score, 1),
        )
        try:
            resp = api_client.post_data(
                OPENAI_API_URL,
                json={
                    "model": DEFAULT_AI_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.4,
                    "max_tokens": 500,
                },
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30,
            )
            content = resp["choices"][0]["message"]["content"]
            result = parse_json_response(content)
            if result and "forecast" in result:
                return result
        except Exception as exc:
            logger.warning("PriceForecaster._openai_forecast failed: %s", exc)
        return None

    def _linear_forecast(self, symbol: str, horizon: int, closes: list) -> dict:
        """Simple linear regression extrapolation as a deterministic fallback."""
        if len(closes) < 2:
            last = closes[0] if closes else 100.0
            forecast = [round(last, 2)] * horizon
            return self._build_result(symbol, horizon, forecast, last, "SIDEWAYS", 0.45, "Insufficient history for trend analysis.")

        n = len(closes)
        x_mean = (n - 1) / 2
        y_mean = sum(closes) / n
        numerator   = sum((i - x_mean) * (closes[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator else 0.0

        last = closes[-1]
        forecast = [round(last + slope * (i + 1), 2) for i in range(horizon)]

        # Confidence interval ± 2% of last price per step
        margin = last * 0.02
        lower = [round(f - margin * (i + 1), 2) for i, f in enumerate(forecast)]
        upper = [round(f + margin * (i + 1), 2) for i, f in enumerate(forecast)]

        trend = "UP" if slope > 0.001 else ("DOWN" if slope < -0.001 else "SIDEWAYS")
        return {
            "symbol": symbol,
            "horizon_days": horizon,
            "forecast": forecast,
            "lower_bound": lower,
            "upper_bound": upper,
            "trend": trend,
            "confidence": 0.55,
            "reasoning": f"Linear trend extrapolation based on {n} historical closes. Slope: {slope:.4f}.",
        }

    @staticmethod
    def _build_result(symbol, horizon, forecast, last, trend, confidence, reasoning):
        margin = last * 0.02
        return {
            "symbol": symbol,
            "horizon_days": horizon,
            "forecast": forecast,
            "lower_bound": [round(f - margin * (i + 1), 2) for i, f in enumerate(forecast)],
            "upper_bound": [round(f + margin * (i + 1), 2) for i, f in enumerate(forecast)],
            "trend": trend,
            "confidence": confidence,
            "reasoning": reasoning,
        }


price_forecaster = PriceForecaster()
