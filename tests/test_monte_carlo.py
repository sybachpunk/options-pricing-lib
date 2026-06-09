"""Monte Carlo: convergence rate, variance reduction effectiveness."""
import math

import pytest

from options_pricing import bs_price, mc_price
from options_pricing.monte_carlo import mc_convergence


@pytest.mark.parametrize("opt", ["call", "put"])
def test_mc_matches_bsm(opt):
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, opt)
    bsm = bs_price(*args)
    res = mc_price(*args, n_paths=200_000, seed=42, return_full=True)
    # Three standard errors gives ~99.7% confidence
    assert abs(res.price - bsm) < 3 * res.std_error + 0.02


def test_mc_std_error_shrinks_like_sqrt_N():
    """SE should fall roughly like 1/sqrt(N); ratio of SE at N and 4N ≈ 2."""
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    r1 = mc_price(*args, n_paths=10_000, seed=1, antithetic=False,
                  control_variate=False, return_full=True)
    r2 = mc_price(*args, n_paths=40_000, seed=1, antithetic=False,
                  control_variate=False, return_full=True)
    ratio = r1.std_error / r2.std_error
    assert 1.6 < ratio < 2.5  # generous band; finite-sample noise


def test_control_variate_reduces_variance():
    """CV should produce a tighter SE than plain MC at the same N."""
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    plain = mc_price(*args, n_paths=20_000, seed=7,
                     antithetic=False, control_variate=False, return_full=True)
    cv = mc_price(*args, n_paths=20_000, seed=7,
                  antithetic=False, control_variate=True, return_full=True)
    assert cv.std_error < plain.std_error


def test_antithetic_reduces_variance():
    args = (100.0, 110.0, 1.0, 0.05, 0.25, 0.0, "call")
    plain = mc_price(*args, n_paths=20_000, seed=7,
                     antithetic=False, control_variate=False, return_full=True)
    anti = mc_price(*args, n_paths=20_000, seed=7,
                    antithetic=True, control_variate=False, return_full=True)
    assert anti.std_error < plain.std_error


def test_antithetic_requires_two_pairs():
    """Antithetic sampling needs >= 2 pairs for a defined standard error."""
    with pytest.raises(ValueError):
        mc_price(100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call",
                 n_paths=3, antithetic=True)


def test_convergence_sweep_runs():
    rows = mc_convergence(100, 100, 1.0, 0.05, 0.25, 0.0, "call",
                          path_counts=[1000, 5000, 20_000], seed=42)
    assert len(rows) == 3
    # SE should be monotone-ish decreasing
    assert rows[0]["std_error"] > rows[2]["std_error"]
