"""
Implied volatility solver.

Given a market price, solve BS(sigma) - market_price = 0 for sigma.
Uses Brent's method (bracketing + inverse quadratic interpolation), which
combines bisection-level robustness with near-superlinear convergence.

Newton's method using vega would be faster but can diverge for deep OTM
options where vega is tiny. Brent is the boring, reliable choice — and it's
what production systems typically use.

Arbitrage bounds:
    Call price must satisfy max(S*exp(-qT) - K*exp(-rT), 0) <= C <= S*exp(-qT)
    Put price  must satisfy max(K*exp(-rT) - S*exp(-qT), 0) <= P <= K*exp(-rT)
If the market price violates these, no implied vol exists and we raise.
"""
from __future__ import annotations

import math

from scipy.optimize import brentq

from .black_scholes import bs_price
from .types import OptionType


def implied_vol(
    market_price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    q: float = 0.0,
    option_type: OptionType = "call",
    sigma_low: float = 1e-6,
    sigma_high: float = 5.0,
    xtol: float = 1e-8,
) -> float:
    """Solve for sigma such that bs_price(sigma) == market_price."""
    if T <= 0:
        raise ValueError("Cannot imply volatility from an expired option")

    disc_r = math.exp(-r * T)
    disc_q = math.exp(-q * T)

    if option_type == "call":
        lower_bound = max(S * disc_q - K * disc_r, 0.0)
        upper_bound = S * disc_q
    else:
        lower_bound = max(K * disc_r - S * disc_q, 0.0)
        upper_bound = K * disc_r

    if market_price < lower_bound - 1e-10 or market_price > upper_bound + 1e-10:
        raise ValueError(
            f"Market price {market_price:.6f} violates arbitrage bounds "
            f"[{lower_bound:.6f}, {upper_bound:.6f}] — no implied vol exists."
        )

    def objective(sigma: float) -> float:
        return bs_price(S, K, T, r, sigma, q, option_type) - market_price

    f_low = objective(sigma_low)
    f_high = objective(sigma_high)
    if f_low * f_high > 0:
        # Either both positive or both negative — widen the high bound once
        sigma_high *= 2
        f_high = objective(sigma_high)
        if f_low * f_high > 0:
            raise ValueError("Could not bracket implied vol; market price may be inconsistent")

    return float(brentq(objective, sigma_low, sigma_high, xtol=xtol))
