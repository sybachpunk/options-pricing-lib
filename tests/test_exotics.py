"""Exotic option sanity checks."""
import math

import numpy as np
import pytest

from options_pricing import (
    asian_price, barrier_price, bs_price, geometric_asian_price,
    geometric_asian_price_discrete,
)
from options_pricing.exotics import _simulate_paths


def test_asian_cheaper_than_european_call():
    """Averaging dampens volatility -> Asian call should be cheaper than vanilla."""
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.30
    vanilla = bs_price(S, K, T, r, sigma, 0.0, "call")
    asian = asian_price(S, K, T, r, sigma, 0.0, "call",
                        n_paths=50_000, n_steps=50, seed=42)
    assert asian.price < vanilla
    # Should be in the ballpark of half — averaging vol reduction is ~ 1/sqrt(3)
    assert asian.price > 0.4 * vanilla


def test_geometric_asian_closed_forms_ordering():
    """The discrete-sampling geometric price sits above the continuous one
    (fewer averaging dates → more variance retained) and converges to it as
    the number of observations grows. Both sit below the vanilla."""
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.25
    cont = geometric_asian_price(S, K, T, r, sigma, 0.0, "call")
    vanilla = bs_price(S, K, T, r, sigma, 0.0, "call")
    assert 0 < cont < vanilla

    gaps = []
    for n in [12, 50, 250, 2000]:
        disc = geometric_asian_price_discrete(S, K, T, r, sigma, 0.0, "call", n_obs=n)
        assert cont < disc < vanilla
        gaps.append(disc - cont)
    # Monotone convergence toward the continuous limit
    assert gaps == sorted(gaps, reverse=True)
    assert gaps[-1] < 0.01


def test_discrete_geometric_closed_form_matches_simulation():
    """The discrete geometric closed form must be the EXACT mean of the
    simulated geometric-average payoff — that's what qualifies it as a
    control variate. Checked within Monte Carlo error."""
    S, K, T, r, sigma, q = 100.0, 100.0, 1.0, 0.05, 0.30, 0.0
    n_steps, n_paths = 25, 200_000
    closed = geometric_asian_price_discrete(S, K, T, r, sigma, q, "call", n_obs=n_steps)

    paths = _simulate_paths(S, T, r, sigma, q, n_paths, n_steps,
                            antithetic=False, seed=123)
    geo_avg = np.exp(np.log(paths[:, 1:]).mean(axis=1))
    payoff = math.exp(-r * T) * np.maximum(geo_avg - K, 0.0)
    mc_mean = payoff.mean()
    mc_se = payoff.std(ddof=1) / math.sqrt(n_paths)

    assert closed == pytest.approx(mc_mean, abs=4 * mc_se)


def test_asian_cv_consistent_with_plain_mc():
    """The control-variate estimator must agree with plain MC on the same
    payoff — the CV may only shrink the error bar, never move the target."""
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.30
    plain = asian_price(S, K, T, r, sigma, 0.0, "call",
                        n_paths=400_000, n_steps=25,
                        control_variate=False, seed=11)
    cv = asian_price(S, K, T, r, sigma, 0.0, "call",
                     n_paths=100_000, n_steps=25,
                     control_variate=True, seed=42)
    tol = 4 * (plain.std_error + cv.std_error) + 1e-3
    assert cv.price == pytest.approx(plain.price, abs=tol)
    # And it should be doing its job: materially tighter error bar
    assert cv.std_error < 0.2 * plain.std_error


def test_barrier_in_out_parity():
    """Knock-in + knock-out = vanilla (with no rebate)."""
    S, K, T, r, sigma, B = 100.0, 100.0, 1.0, 0.05, 0.25, 120.0
    out = barrier_price(S, K, T, r, sigma, B, "up-and-out", 0.0, "call",
                        n_paths=50_000, n_steps=252, seed=42)
    inn = barrier_price(S, K, T, r, sigma, B, "up-and-in", 0.0, "call",
                        n_paths=50_000, n_steps=252, seed=42)
    vanilla = bs_price(S, K, T, r, sigma, 0.0, "call")
    combined = out.price + inn.price
    # Loose MC tolerance: ~3 * (out.std_error + in.std_error)
    tol = 3 * (out.std_error + inn.std_error) + 0.05
    assert combined == pytest.approx(vanilla, abs=tol)
