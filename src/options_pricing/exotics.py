"""
Exotic options via Monte Carlo path simulation.

Implements:
    - Arithmetic-average Asian call/put with geometric-Asian control variate
    - Knock-in / knock-out barrier options (up/down, in/out)

Why Monte Carlo for these:
    Asian and barrier payoffs depend on the path, not just the terminal value.
    There's no clean closed form for arithmetic Asians (the sum of correlated
    lognormals is not lognormal). Geometric Asians DO have a closed form,
    which makes them an ideal control variate for their arithmetic siblings —
    the two payoffs are >99% correlated.

Control-variate discipline:
    A control variate only removes variance cleanly if its expected value is
    EXACT for the control as simulated. The MC here averages over n_steps
    discrete observation dates, so the control's mean comes from the
    discrete-sampling geometric closed form (`geometric_asian_price_discrete`)
    with the same number of observations — not the continuous-averaging
    Kemna-Vorst formula, whose mean differs materially at coarse sampling
    (~0.13 on an ATM 1y call at 50 observations).

Barrier accuracy:
    Discrete monitoring misses barrier crossings between observation times,
    biasing knock-out prices high (knock-ins low). Use many time steps
    (>=250/year) or implement a Brownian-bridge correction for production.
    We don't here — this is portfolio code, and the limitation is documented.

Error reporting:
    With antithetic sampling, each (Z, -Z) pair is averaged into a single
    observation before the standard error is computed, so the reported SE is
    a valid i.i.d. estimate that reflects the genuine variance reduction.
"""
from __future__ import annotations

import math
from typing import Literal, Optional

import numpy as np
from scipy.stats import norm

from .black_scholes import bs_price
from .types import OptionType, PricingResult

BarrierKind = Literal["up-and-out", "down-and-out", "up-and-in", "down-and-in"]


def _simulate_paths(
    S: float, T: float, r: float, sigma: float, q: float,
    n_paths: int, n_steps: int, antithetic: bool, seed: Optional[int],
) -> np.ndarray:
    """Return an (n_paths, n_steps+1) matrix of simulated prices."""
    rng = np.random.default_rng(seed)
    dt = T / n_steps
    drift = (r - q - 0.5 * sigma * sigma) * dt
    vol = sigma * math.sqrt(dt)

    if antithetic:
        half = n_paths // 2
        Z_half = rng.standard_normal((half, n_steps))
        Z = np.vstack([Z_half, -Z_half])
    else:
        Z = rng.standard_normal((n_paths, n_steps))

    log_increments = drift + vol * Z
    log_paths = np.cumsum(log_increments, axis=1)
    paths = S * np.exp(log_paths)
    # Prepend the initial price
    paths = np.hstack([np.full((paths.shape[0], 1), S), paths])
    return paths


def geometric_asian_price(
    S: float, K: float, T: float, r: float, sigma: float,
    q: float = 0.0, option_type: OptionType = "call",
) -> float:
    """
    Closed-form geometric-average Asian (continuous sampling, Kemna-Vorst).

    The geometric average over [0,T] is lognormal, so the option price has
    the BSM form with adjusted parameters:
        sigma_geo = sigma / sqrt(3)
        q_geo     = 0.5*(r + q) + sigma**2 / 12
    """
    sigma_geo = sigma / math.sqrt(3.0)
    q_geo = 0.5 * (r + q) + sigma * sigma / 12.0
    return bs_price(S, K, T, r, sigma_geo, q_geo, option_type)


def geometric_asian_price_discrete(
    S: float, K: float, T: float, r: float, sigma: float,
    q: float = 0.0, option_type: OptionType = "call", n_obs: int = 50,
) -> float:
    """
    Closed-form geometric-average Asian with DISCRETE sampling at the n_obs
    equally spaced dates t_i = i*T/n, i = 1..n.

    The log of the geometric mean of jointly lognormal observations is
    Gaussian with
        m = ln S + (r - q - sigma^2/2) * T * (n+1) / (2n)
        v = sigma^2 * T * (n+1)(2n+1) / (6 n^2)
    so the option prices in Black form on the "forward" exp(m + v/2).

    As n -> inf this converges to the continuous-averaging formula in
    `geometric_asian_price`. Use THIS version as the control-variate mean for
    a discretely sampled MC — the observation dates must match exactly.
    """
    if n_obs < 1:
        raise ValueError("n_obs must be >= 1")
    if T <= 0 or sigma <= 0:
        # Deterministic limit: geometric mean of the forward curve.
        m = math.log(S) + (r - q - 0.5 * sigma * sigma) * T * (n_obs + 1) / (2 * n_obs)
        G = math.exp(m)
        intrinsic = max(G - K, 0.0) if option_type == "call" else max(K - G, 0.0)
        return math.exp(-r * T) * intrinsic

    n = n_obs
    m = math.log(S) + (r - q - 0.5 * sigma * sigma) * T * (n + 1) / (2 * n)
    v = sigma * sigma * T * (n + 1) * (2 * n + 1) / (6.0 * n * n)
    sv = math.sqrt(v)
    d1 = (m - math.log(K) + v) / sv
    d2 = d1 - sv
    G_fwd = math.exp(m + 0.5 * v)
    disc = math.exp(-r * T)
    if option_type == "call":
        return disc * (G_fwd * norm.cdf(d1) - K * norm.cdf(d2))
    return disc * (K * norm.cdf(-d2) - G_fwd * norm.cdf(-d1))


def _pair_average(x: np.ndarray) -> np.ndarray:
    """Average antithetic (Z, -Z) rows into one observation per pair, so a
    sample standard error over the result is an i.i.d. estimate."""
    half = len(x) // 2
    return 0.5 * (x[:half] + x[half:])


def asian_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: OptionType = "call",
    n_paths: int = 100_000,
    n_steps: int = 100,
    antithetic: bool = True,
    control_variate: bool = True,
    seed: Optional[int] = None,
) -> PricingResult:
    """
    Arithmetic-average Asian option via Monte Carlo, with geometric-Asian
    control variate.

    The control's expected value is the DISCRETE-sampling geometric closed
    form evaluated at the same n_steps observation dates the simulation uses,
    so the control variate is exact for the simulated quantity.
    """
    if antithetic and n_paths < 4:
        raise ValueError("n_paths must be >= 4 when antithetic (need >= 2 pairs)")

    paths = _simulate_paths(S, T, r, sigma, q, n_paths, n_steps, antithetic, seed)
    # Average over the n_steps observation dates (skip t=0, the spot)
    arith_avg = paths[:, 1:].mean(axis=1)
    geo_avg = np.exp(np.log(paths[:, 1:]).mean(axis=1))

    if option_type == "call":
        arith_payoff = np.maximum(arith_avg - K, 0.0)
        geo_payoff = np.maximum(geo_avg - K, 0.0)
    else:
        arith_payoff = np.maximum(K - arith_avg, 0.0)
        geo_payoff = np.maximum(K - geo_avg, 0.0)

    disc = math.exp(-r * T)
    arith_disc = disc * arith_payoff
    geo_disc = disc * geo_payoff

    # Collapse antithetic pairs into single observations so the SE below is
    # an i.i.d. estimate that credits the antithetic variance reduction.
    if antithetic:
        arith_disc = _pair_average(arith_disc)
        geo_disc = _pair_average(geo_disc)
    n_eff = len(arith_disc)

    if control_variate:
        # Match the simulation's discrete observation dates exactly.
        mu_geo = geometric_asian_price_discrete(
            S, K, T, r, sigma, q, option_type, n_obs=n_steps
        )
        cov = np.cov(arith_disc, geo_disc, ddof=1)
        var_geo = cov[1, 1]
        if var_geo > 0:
            beta = cov[0, 1] / var_geo
            adjusted = arith_disc - beta * (geo_disc - mu_geo)
            price = float(np.mean(adjusted))
            std_err = float(np.std(adjusted, ddof=1) / math.sqrt(n_eff))
        else:
            price = float(np.mean(arith_disc))
            std_err = float(np.std(arith_disc, ddof=1) / math.sqrt(n_eff))
    else:
        price = float(np.mean(arith_disc))
        std_err = float(np.std(arith_disc, ddof=1) / math.sqrt(n_eff))

    return PricingResult(
        price=price,
        method="monte_carlo_asian",
        std_error=std_err,
        n_paths=n_paths,
        n_steps=n_steps,
        extras={"antithetic": antithetic, "control_variate": control_variate},
    )


def barrier_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    barrier: float,
    kind: BarrierKind,
    q: float = 0.0,
    option_type: OptionType = "call",
    n_paths: int = 100_000,
    n_steps: int = 252,
    antithetic: bool = True,
    seed: Optional[int] = None,
    rebate: float = 0.0,
) -> PricingResult:
    """
    Single-barrier knock-in / knock-out option via Monte Carlo.

    `kind` selects the barrier flavor; `barrier` is the level B.
    `rebate` is paid if a knock-out option is knocked out (defaults to 0).
    """
    if barrier <= 0:
        raise ValueError("barrier must be positive")
    if "up" in kind and barrier <= S:
        raise ValueError("up-barrier must be strictly above spot")
    if "down" in kind and barrier >= S:
        raise ValueError("down-barrier must be strictly below spot")
    if antithetic and n_paths < 4:
        raise ValueError("n_paths must be >= 4 when antithetic (need >= 2 pairs)")

    paths = _simulate_paths(S, T, r, sigma, q, n_paths, n_steps, antithetic, seed)
    ST = paths[:, -1]

    if "up" in kind:
        breached = paths.max(axis=1) >= barrier
    else:
        breached = paths.min(axis=1) <= barrier

    if option_type == "call":
        vanilla_payoff = np.maximum(ST - K, 0.0)
    else:
        vanilla_payoff = np.maximum(K - ST, 0.0)

    if kind.endswith("-out"):
        payoff = np.where(breached, rebate, vanilla_payoff)
    else:  # in
        payoff = np.where(breached, vanilla_payoff, 0.0)

    disc = math.exp(-r * T)
    discounted = disc * payoff
    # Collapse antithetic pairs into single observations for a valid SE
    # (fraction_breached below stays per-path, computed before pairing).
    if antithetic:
        discounted = _pair_average(discounted)
    price = float(np.mean(discounted))
    std_err = float(np.std(discounted, ddof=1) / math.sqrt(len(discounted)))

    return PricingResult(
        price=price,
        method="monte_carlo_barrier",
        std_error=std_err,
        n_paths=n_paths,
        n_steps=n_steps,
        extras={
            "barrier": barrier,
            "kind": kind,
            "antithetic": antithetic,
            "fraction_breached": float(breached.mean()),
        },
    )
