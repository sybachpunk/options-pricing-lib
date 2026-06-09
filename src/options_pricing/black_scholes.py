"""
Black-Scholes-Merton closed-form pricing and analytical Greeks.

Derivation sketch:
    Under the risk-neutral measure Q, the asset follows
        dS = (r - q) S dt + sigma S dW
    so log S_T ~ N(log S + (r - q - sigma^2/2) T, sigma^2 T).
    A European call payoff max(S_T - K, 0) discounted at e^{-rT}, taken under Q,
    is the closed-form integral that Black, Scholes, and Merton solved.

Assumptions:
    - Constant volatility and risk-free rate
    - Continuous trading, no transaction costs
    - Continuous dividend yield q (set q=0 for non-dividend asset)
    - European exercise only
    - GBM dynamics (lognormal terminal distribution)
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np
from scipy.stats import norm

from .types import Greeks, OptionType

_EPS = 1e-12


def bs_d1_d2(
    S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0
) -> Tuple[float, float]:
    """Return (d1, d2) for Black-Scholes-Merton."""
    if T <= _EPS or sigma <= _EPS:
        # Degenerate limit: the terminal distribution collapses onto the
        # forward F = S*exp((r-q)T), so moneyness is decided by F vs K
        # (equivalently S*e^{-qT} vs K*e^{-rT}), not spot vs strike.
        fwd = S * math.exp((r - q) * T)
        inf = math.inf if fwd > K else -math.inf
        return inf, inf
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    return d1, d2


def bs_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: OptionType = "call",
) -> float:
    """Closed-form European option price under BSM."""
    if T <= _EPS or sigma <= _EPS:
        # Deterministic limit: with no remaining variance the payoff is known
        # today — it's the discounted payoff evaluated at the forward.
        # At T -> 0 the forward collapses to spot, so this also covers expiry.
        fwd = S * math.exp((r - q) * T)
        intrinsic = max(fwd - K, 0.0) if option_type == "call" else max(K - fwd, 0.0)
        return float(math.exp(-r * T) * intrinsic)
    d1, d2 = bs_d1_d2(S, K, T, r, sigma, q)
    disc_r = math.exp(-r * T)
    disc_q = math.exp(-q * T)
    if option_type == "call":
        return float(S * disc_q * norm.cdf(d1) - K * disc_r * norm.cdf(d2))
    return float(K * disc_r * norm.cdf(-d2) - S * disc_q * norm.cdf(-d1))


def bs_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: OptionType = "call",
) -> Greeks:
    """
    Analytical Greeks. Conventions:
        delta = dP/dS
        gamma = d2P/dS2
        vega  = dP/d(sigma)               (per 1.0 of vol; divide by 100 for per-1%)
        theta = -dP/dT                    (calendar-time decay; negative for long options)
        rho   = dP/dr                     (per 1.0 of r; divide by 100 for per-1%)
    """
    if T <= _EPS or sigma <= _EPS:
        # Deterministic limit: the option behaves like a forward position when
        # in the money (on forward moneyness), so delta is the discounted
        # hedge ratio and the convexity Greeks collapse (gamma concentrates
        # into a point mass at F = K).
        fwd = S * math.exp((r - q) * T)
        if option_type == "call":
            delta = math.exp(-q * T) if fwd > K else 0.0
        else:
            delta = -math.exp(-q * T) if fwd < K else 0.0
        return Greeks(delta, 0.0, 0.0, 0.0, 0.0)

    d1, d2 = bs_d1_d2(S, K, T, r, sigma, q)
    sqrtT = math.sqrt(T)
    pdf_d1 = norm.pdf(d1)
    disc_r = math.exp(-r * T)
    disc_q = math.exp(-q * T)

    gamma = disc_q * pdf_d1 / (S * sigma * sqrtT)
    vega = S * disc_q * pdf_d1 * sqrtT

    if option_type == "call":
        delta = disc_q * norm.cdf(d1)
        theta = (
            -S * disc_q * pdf_d1 * sigma / (2 * sqrtT)
            - r * K * disc_r * norm.cdf(d2)
            + q * S * disc_q * norm.cdf(d1)
        )
        rho = K * T * disc_r * norm.cdf(d2)
    else:
        delta = -disc_q * norm.cdf(-d1)
        theta = (
            -S * disc_q * pdf_d1 * sigma / (2 * sqrtT)
            + r * K * disc_r * norm.cdf(-d2)
            - q * S * disc_q * norm.cdf(-d1)
        )
        rho = -K * T * disc_r * norm.cdf(-d2)

    return Greeks(
        delta=float(delta),
        gamma=float(gamma),
        vega=float(vega),
        theta=float(theta),
        rho=float(rho),
    )


def bs_price_vec(
    S: np.ndarray | float,
    K: np.ndarray | float,
    T: np.ndarray | float,
    r: np.ndarray | float,
    sigma: np.ndarray | float,
    q: np.ndarray | float = 0.0,
    option_type: OptionType = "call",
) -> np.ndarray:
    """Vectorized BSM price. Inputs may be scalars or broadcastable arrays."""
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    r = np.asarray(r, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    q = np.asarray(q, dtype=float)

    sqrtT = np.sqrt(np.maximum(T, _EPS))
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    disc_r = np.exp(-r * T)
    disc_q = np.exp(-q * T)

    if option_type == "call":
        out = S * disc_q * norm.cdf(d1) - K * disc_r * norm.cdf(d2)
    else:
        out = K * disc_r * norm.cdf(-d2) - S * disc_q * norm.cdf(-d1)
    return np.asarray(out, dtype=float)
