"""
Monte Carlo pricing for European options.

Method:
    Under risk-neutral measure, S_T = S * exp((r - q - sigma^2/2)*T + sigma*sqrt(T)*Z),
    Z ~ N(0,1). Price = exp(-rT) * E[payoff(S_T)].

Variance reduction:
    - Antithetic variates: pair each Z with -Z. Since the payoff is monotone in
      Z (for vanilla calls/puts after enough ITM-ness), the paired estimators
      are negatively correlated → lower variance than 2N independent samples.
    - Control variate: use discounted S_T as a control. We know analytically
      that E[exp(-rT) * S_T] = S * exp(-qT). Subtract beta * (X_hat - mu_X)
      from the payoff mean, where beta is estimated from the sample covariance.

Convergence:
    Plain MC standard error is sigma_payoff / sqrt(N), i.e. O(1/sqrt(N)).
    Doubling accuracy needs 4x the samples. Variance-reduction techniques
    multiply the constant in front but do not change the rate.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np

from .types import OptionType, PricingResult


def _payoff(ST: np.ndarray, K: float, option_type: OptionType) -> np.ndarray:
    if option_type == "call":
        return np.maximum(ST - K, 0.0)
    return np.maximum(K - ST, 0.0)


def mc_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: OptionType = "call",
    n_paths: int = 100_000,
    antithetic: bool = True,
    control_variate: bool = True,
    seed: Optional[int] = None,
    return_full: bool = False,
) -> PricingResult | float:
    """
    Monte Carlo price for a European call/put under GBM.

    Args:
        n_paths: total number of terminal samples. If antithetic=True, half
                 are generated from independent normals and the other half are
                 their negatives, and at least 4 paths (2 pairs) are required
                 so a sample standard error is defined.
        return_full: if True, return a PricingResult (price + std error +
                     diagnostics). If False, return the price as a float.
    """
    if n_paths < 2:
        raise ValueError("n_paths must be >= 2")
    if antithetic and n_paths < 4:
        raise ValueError("n_paths must be >= 4 when antithetic (need >= 2 pairs)")
    if T <= 0:
        price = max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
        if return_full:
            return PricingResult(price=price, method="monte_carlo", std_error=0.0, n_paths=n_paths)
        return price

    rng = np.random.default_rng(seed)

    drift = (r - q - 0.5 * sigma * sigma) * T
    vol = sigma * math.sqrt(T)
    disc = math.exp(-r * T)
    mu_X = S * math.exp(-q * T)  # known mean of disc * S_T

    # Build per-sample observations Y (discounted payoff) and X (control).
    # When antithetic, each "sample" is the AVERAGE of the (Z, -Z) pair —
    # so the reported std_err reflects the genuine variance reduction.
    if antithetic:
        n_pairs = n_paths // 2
        Z = rng.standard_normal(n_pairs)
        ST_pos = S * np.exp(drift + vol * Z)
        ST_neg = S * np.exp(drift - vol * Z)
        Y = 0.5 * disc * (_payoff(ST_pos, K, option_type)
                          + _payoff(ST_neg, K, option_type))
        X = 0.5 * disc * (ST_pos + ST_neg)
        n_eff = n_pairs
    else:
        Z = rng.standard_normal(n_paths)
        ST = S * np.exp(drift + vol * Z)
        Y = disc * _payoff(ST, K, option_type)
        X = disc * ST
        n_eff = n_paths

    if control_variate:
        cov = np.cov(Y, X, ddof=1)
        var_X = cov[1, 1]
        if var_X > 0:
            beta = cov[0, 1] / var_X
            adjusted = Y - beta * (X - mu_X)
            price = float(np.mean(adjusted))
            std_err = float(np.std(adjusted, ddof=1) / math.sqrt(n_eff))
        else:
            price = float(np.mean(Y))
            std_err = float(np.std(Y, ddof=1) / math.sqrt(n_eff))
    else:
        price = float(np.mean(Y))
        std_err = float(np.std(Y, ddof=1) / math.sqrt(n_eff))

    if return_full:
        return PricingResult(
            price=price,
            method="monte_carlo",
            std_error=std_err,
            n_paths=n_paths,
            extras={"antithetic": antithetic, "control_variate": control_variate},
        )
    return price


def mc_convergence(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: OptionType = "call",
    path_counts: Optional[list[int]] = None,
    antithetic: bool = True,
    control_variate: bool = True,
    seed: int = 42,
) -> list[dict]:
    """Run MC at multiple sample sizes and return a list of result rows."""
    if path_counts is None:
        path_counts = [1_000, 2_000, 5_000, 10_000, 20_000, 50_000, 100_000, 200_000, 500_000]

    rows: list[dict] = []
    for n in path_counts:
        res = mc_price(
            S, K, T, r, sigma, q, option_type,
            n_paths=n,
            antithetic=antithetic,
            control_variate=control_variate,
            seed=seed,
            return_full=True,
        )
        assert isinstance(res, PricingResult)
        rows.append({
            "n_paths": n,
            "price": res.price,
            "std_error": res.std_error,
        })
    return rows
