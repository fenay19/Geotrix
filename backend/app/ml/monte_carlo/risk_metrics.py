"""
Risk Metrics Calculator
========================
Computes institutional-grade risk metrics from the Monte Carlo simulation
price path matrix produced by GBMEngine.

Metrics implemented:
  - VaR    : Value at Risk (maximum expected loss at a confidence level)
  - CVaR   : Conditional VaR / Expected Shortfall (average of worst losses)
  - P(loss): Probability of ending below the starting price
  - Sharpe : Annualized Sharpe Ratio from simulated paths
  - Expected Return: Mean final return across all paths

All inputs are the raw np.ndarray (n_sims, horizon) from GBMEngine.
All outputs are plain Python floats — safe for JSON serialization.
"""

import logging
import math
import numpy as np

logger = logging.getLogger("geotrade.ml.monte_carlo.risk")


class RiskMetrics:
    """
    Computes financial risk metrics from a Monte Carlo price path matrix.

    All methods accept:
        price_paths : np.ndarray, shape (n_sims, horizon)
        S0          : float, the starting price used in the simulation

    The 'horizon end' price of each simulation is price_paths[:, -1].
    """

    # ── Core Risk Metrics ─────────────────────────────────────────────────────

    def compute_var(
        self,
        price_paths: np.ndarray,
        S0: float,
        confidence: float = 0.95,
    ) -> float:
        """
        Value at Risk (VaR).

        The maximum loss (in price units) you would NOT expect to exceed
        with the given confidence level over the simulation horizon.

        Example: VaR_95 = -6.30 means: in 95% of scenarios, loss ≤ $6.30.

        Returns a positive number representing the loss magnitude.
        """
        final_prices = price_paths[:, -1]                # terminal prices
        returns = (final_prices - S0) / S0               # % returns
        # VaR is the (1 - confidence) quantile of the loss distribution
        var_return = float(np.percentile(returns, (1 - confidence) * 100))
        var_price  = var_return * S0                     # convert to price units
        return round(abs(var_price), 4)                  # return as positive loss

    def compute_cvar(
        self,
        price_paths: np.ndarray,
        S0: float,
        confidence: float = 0.95,
    ) -> float:
        """
        Conditional Value at Risk (CVaR) / Expected Shortfall.

        The average loss across the worst (1-confidence)% of scenarios.
        Always >= VaR. More conservative than VaR.

        Example: CVaR_95 = -8.10 means: in the worst 5% of scenarios,
        average loss = $8.10.

        Returns a positive number representing the average loss magnitude.
        """
        final_prices = price_paths[:, -1]
        returns = (final_prices - S0) / S0
        cutoff = np.percentile(returns, (1 - confidence) * 100)
        tail_returns = returns[returns <= cutoff]
        if len(tail_returns) == 0:
            return 0.0
        cvar_return = float(tail_returns.mean())
        cvar_price  = cvar_return * S0
        return round(abs(cvar_price), 4)

    def compute_probability_of_loss(
        self,
        price_paths: np.ndarray,
        S0: float,
    ) -> float:
        """
        Probability of Loss.

        The fraction (0-1) of simulation paths that end below S0 (the
        starting price), i.e. the probability the investment loses money.

        Example: 0.684 → 68.4% of paths end below current price.
        """
        final_prices = price_paths[:, -1]
        prob = float((final_prices < S0).mean())
        return round(prob, 4)

    def compute_sharpe_ratio(
        self,
        price_paths: np.ndarray,
        S0: float,
        horizon: int = 30,
        risk_free_rate: float = 0.05,
    ) -> float:
        """
        Annualized Sharpe Ratio from simulated paths.

        Sharpe = (Mean Annualized Return - Risk-Free Rate) / Annualized Std Dev

        Args:
            horizon:          Number of trading days in the simulation.
            risk_free_rate:   Annual risk-free rate (default 5%).

        Returns:
            Sharpe ratio as a float. Positive = good, > 1.0 = excellent.
        """
        final_prices = price_paths[:, -1]
        period_returns = (final_prices - S0) / S0

        # Annualize: scale by trading days per year
        ann_factor = 252.0 / horizon
        mean_ann_return = float(period_returns.mean()) * ann_factor
        std_period      = float(period_returns.std())
        std_ann         = std_period * math.sqrt(ann_factor)

        if std_ann == 0:
            return 0.0

        sharpe = (mean_ann_return - risk_free_rate) / std_ann
        return round(sharpe, 4)

    def compute_expected_return(
        self,
        price_paths: np.ndarray,
        S0: float,
    ) -> float:
        """
        Expected (mean) percentage return across all simulation paths at horizon end.

        Example: 0.032 → expected return of +3.2% over the horizon.
        """
        final_prices = price_paths[:, -1]
        mean_return = float(((final_prices - S0) / S0).mean())
        return round(mean_return, 4)

    # ── Convenience: Full Report ──────────────────────────────────────────────

    def full_report(
        self,
        price_paths: np.ndarray,
        S0: float,
        horizon: int = 30,
        confidence: float = 0.95,
        risk_free_rate: float = 0.05,
    ) -> dict:
        """
        Computes all risk metrics in one call.

        Returns:
            {
                "var_95":              float  — Value at Risk (price units, positive = loss)
                "cvar_95":             float  — Conditional VaR (price units, positive = loss)
                "probability_of_loss": float  — Fraction of paths ending below S0
                "expected_return":     float  — Mean return across all paths
                "sharpe_ratio":        float  — Annualized Sharpe Ratio
                "best_case":           float  — 99th percentile final price
                "worst_case":          float  — 1st percentile final price
                "median_final_price":  float  — 50th percentile final price
                "confidence_level":    float  — Confidence level used for VaR/CVaR
                "n_simulations":       int
            }
        """
        final_prices = price_paths[:, -1]

        return {
            "var_95":              self.compute_var(price_paths, S0, confidence),
            "cvar_95":             self.compute_cvar(price_paths, S0, confidence),
            "probability_of_loss": self.compute_probability_of_loss(price_paths, S0),
            "expected_return":     self.compute_expected_return(price_paths, S0),
            "sharpe_ratio":        self.compute_sharpe_ratio(price_paths, S0, horizon, risk_free_rate),
            "best_case":           round(float(np.percentile(final_prices, 99)), 4),
            "worst_case":          round(float(np.percentile(final_prices,  1)), 4),
            "median_final_price":  round(float(np.percentile(final_prices, 50)), 4),
            "confidence_level":    confidence,
            "n_simulations":       price_paths.shape[0],
        }


# Module-level singleton
risk_metrics = RiskMetrics()
