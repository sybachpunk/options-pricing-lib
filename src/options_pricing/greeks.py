"""
Finite-difference Greeks.

Used in two ways throughout the codebase:
    1. As a sanity check on the closed-form BSM Greeks — bumping inputs
       and re-pricing should recover the analytical derivatives.
    2. As the only Greek-extraction method available for Monte Carlo and
       exotic payoffs where no closed form exists.

All derivatives are computed with centered differences (O(h^2) accuracy):
    f'(x) ≈ (f(x+h) - f(x-h)) / (2h)
    f''(x) ≈ (f(x+h) - 2 f(x) + f(x-h)) / h^2

Bump sizes are chosen as a fraction of the input magnitude for delta/gamma,
and absolute for the others (since vol/rates have natural absolute scale).
"""
from __future__ import annotations

from typing import Callable

from .types import Greeks, OptionType


# Pricer signature: f(S, K, T, r, sigma, q, option_type) -> price
Pricer = Callable[..., float]


def fd_greeks(
    pricer: Pricer,
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: OptionType = "call",
    h_S_rel: float = 1e-2,
    h_sigma: float = 1e-3,
    h_T: float = 1e-3,
    h_r: float = 1e-4,
    **pricer_kwargs,
) -> Greeks:
    """
    Compute Greeks by finite-differencing an arbitrary pricer.

    Args:
        pricer: callable matching f(S, K, T, r, sigma, q, option_type, **kwargs) -> price
        h_S_rel: relative bump for S (e.g., 0.01 = 1% of S)
        h_sigma, h_T, h_r: absolute bumps
        pricer_kwargs: forwarded to pricer (e.g., n_steps=500 for binomial,
                       n_paths=200_000 + seed=42 for MC — set a fixed seed for
                       MC or the noise will dominate the bump signal)
    """
    h_S = max(h_S_rel * S, 1e-4)

    def f(S_, K_, T_, r_, sigma_, q_):
        return pricer(S_, K_, T_, r_, sigma_, q_, option_type, **pricer_kwargs)

    p0 = f(S, K, T, r, sigma, q)

    # Delta and gamma (vary S)
    p_S_up = f(S + h_S, K, T, r, sigma, q)
    p_S_dn = f(S - h_S, K, T, r, sigma, q)
    delta = (p_S_up - p_S_dn) / (2 * h_S)
    gamma = (p_S_up - 2 * p0 + p_S_dn) / (h_S * h_S)

    # Vega
    p_v_up = f(S, K, T, r, sigma + h_sigma, q)
    p_v_dn = f(S, K, T, r, sigma - h_sigma, q)
    vega = (p_v_up - p_v_dn) / (2 * h_sigma)

    # Theta (theta = -dP/dT; we differentiate P wrt T-to-expiry then flip sign)
    # If T is very small, use forward difference to avoid negative T.
    if T - h_T > 0:
        p_T_up = f(S, K, T + h_T, r, sigma, q)
        p_T_dn = f(S, K, T - h_T, r, sigma, q)
        theta = -(p_T_up - p_T_dn) / (2 * h_T)
    else:
        p_T_up = f(S, K, T + h_T, r, sigma, q)
        theta = -(p_T_up - p0) / h_T

    # Rho
    p_r_up = f(S, K, T, r + h_r, sigma, q)
    p_r_dn = f(S, K, T, r - h_r, sigma, q)
    rho = (p_r_up - p_r_dn) / (2 * h_r)

    return Greeks(
        delta=float(delta),
        gamma=float(gamma),
        vega=float(vega),
        theta=float(theta),
        rho=float(rho),
    )
