"""
GBM Monte Carlo Simulation Engine
===================================
Implements Geometric Brownian Motion (GBM) to simulate 10,000 possible
future price paths for a financial asset.

The Math:
    S(t+1) = S(t) × exp( (μ - σ²/2)·Δt + σ·√Δt·Z )

    where:
        μ  = drift       (expected return, from ML model output)
        σ  = volatility  (annualized std dev, from ML model output)
        Δt = 1/252       (one trading day as a fraction of a year)
        Z  = N(0,1)      (standard normal random draw)

All paths are fully NumPy-vectorized — 10,000 simulations run in < 50ms.
"""

import logging
import numpy as np
from typing import Optional

logger = logging.getLogger("geotrade.ml.monte_carlo.gbm")

# One trading day as fraction of a year (252 trading days / year)
TRADING_DT: float = 1.0 / 252.0


class GBMEngine:
    """
    Geometric Brownian Motion simulation engine.
    Takes a starting price, drift (μ), and volatility (σ) — typically
    sourced from the Stage 2 ML model — and simulates N price paths over
    a given horizon using fully vectorized NumPy operations.
    """

    def run_simulation(
        self,
        S0: float,
        drift: float,
        volatility: float,
        horizon: int = 30,
        n_sims: int = 10_000,
        dt: float = TRADING_DT,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """
        Simulates price paths using GBM.

        Args:
            S0:         Current (starting) price.
            drift:      Annualized expected return (μ), e.g. -0.03 for -3%.
                        Sourced from the ML drift regressor.
            volatility: Annualized volatility (σ), e.g. 0.20 for 20%.
                        Sourced from the ML volatility regressor.
            horizon:    Number of trading days to simulate.
            n_sims:     Number of independent simulation paths.
            dt:         Time step size (default 1/252 = one trading day).
            seed:       Optional random seed for reproducibility.

        Returns:
            np.ndarray of shape (n_sims, horizon) — each row is one price path.
            Values are absolute prices, not returns.
        """
        if seed is not None:
            np.random.seed(seed)

        if S0 <= 0:
            raise ValueError(f"Starting price S0 must be positive, got {S0}")
        if volatility < 0:
            raise ValueError(f"Volatility must be non-negative, got {volatility}")
        if horizon < 1:
            raise ValueError(f"Horizon must be >= 1, got {horizon}")

        # Z: matrix of standard normal random draws — shape (n_sims, horizon)
        Z = np.random.standard_normal((n_sims, horizon))

        # GBM log-return for each time step:
        # log_return = (μ - σ²/2)·Δt + σ·√Δt·Z
        log_returns = (drift - 0.5 * volatility ** 2) * dt \
                      + volatility * np.sqrt(dt) * Z

        # Cumulative sum of log-returns, then exponentiate to get price paths
        # price_paths[i, t] = S0 * exp(sum of log_returns from 0 to t)
        price_paths = S0 * np.exp(np.cumsum(log_returns, axis=1))

        logger.debug(
            "GBM simulation complete: S0=%.2f, μ=%.4f, σ=%.4f, "
            "horizon=%d days, n_sims=%d",
            S0, drift, volatility, horizon, n_sims,
        )

        return price_paths  # shape: (n_sims, horizon)

    def run_garch_simulation(
        self,
        S0: float,
        garch_params: dict,
        current_var: float,
        horizon: int = 30,
        n_sims: int = 10_000,
        seed: Optional[int] = None,
    ) -> np.ndarray:
        """
        Simulates price paths using a dynamic, time-varying GARCH(1,1) volatility framework.

        Args:
            S0:           Starting price.
            garch_params: Dict containing 'mu', 'omega', 'alpha', and 'beta'.
            current_var:  Current scaled conditional variance (scaled by 100).
            horizon:      Trading days to simulate forward.
            n_sims:       Number of paths.
            seed:         Optional random seed.
        """
        if seed is not None:
            np.random.seed(seed)

        mu = garch_params.get("mu", 0.0)
        omega = garch_params.get("omega", 0.01)
        alpha = garch_params.get("alpha", 0.05)
        beta = garch_params.get("beta", 0.90)

        # Initialize paths matrix
        price_paths = np.zeros((n_sims, horizon))

        # Vectorized variance tracker: shape (n_sims,)
        h = np.ones(n_sims) * current_var
        current_prices = np.ones(n_sims) * S0

        for t in range(horizon):
            Z = np.random.standard_normal(n_sims)
            # Scaled return shock: epsilon = sqrt(h_t) * Z_t
            shocks = np.sqrt(np.clip(h, 1e-6, None)) * Z
            # Scaled return: r = mu + epsilon
            r = mu + shocks
            # Raw return: R = r / 100.0
            R = r / 100.0
            
            # Evolve price: S_t+1 = S_t * exp(R)
            current_prices = current_prices * np.exp(R)
            price_paths[:, t] = current_prices
            
            # Evolve conditional variance: h_t+1 = omega + alpha * epsilon^2 + beta * h_t
            h = omega + alpha * (shocks ** 2) + beta * h

        return price_paths


    def summarize(self, price_paths: np.ndarray) -> dict:
        """
        Extracts the key percentile paths from the simulation matrix.

        Args:
            price_paths: np.ndarray of shape (n_sims, horizon).

        Returns:
            {
                "median":    list[float]  — 50th percentile (expected path)
                "upper_95":  list[float]  — 95th percentile (optimistic bound)
                "lower_05":  list[float]  — 5th percentile  (pessimistic bound)
                "upper_75":  list[float]  — 75th percentile
                "lower_25":  list[float]  — 25th percentile
                "mean":      list[float]  — mean path across all simulations
            }
        """
        return {
            "median":   np.percentile(price_paths, 50, axis=0).round(4).tolist(),
            "upper_95": np.percentile(price_paths, 95, axis=0).round(4).tolist(),
            "lower_05": np.percentile(price_paths, 5,  axis=0).round(4).tolist(),
            "upper_75": np.percentile(price_paths, 75, axis=0).round(4).tolist(),
            "lower_25": np.percentile(price_paths, 25, axis=0).round(4).tolist(),
            "mean":     price_paths.mean(axis=0).round(4).tolist(),
        }


# Module-level singleton
gbm_engine = GBMEngine()
