"""Cross-validation: analytical Greeks vs. finite differences."""
import pytest

from options_pricing import bs_greeks, bs_price, fd_greeks


CASES = [
    (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call"),
    (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "put"),
    (100.0, 110.0, 0.5, 0.03, 0.20, 0.02, "call"),
    (100.0, 90.0, 2.0, 0.04, 0.30, 0.01, "put"),
    (50.0, 100.0, 1.0, 0.05, 0.40, 0.0, "call"),  # deep OTM
    (150.0, 100.0, 1.0, 0.05, 0.20, 0.0, "call"),  # deep ITM
]


@pytest.mark.parametrize("S,K,T,r,sigma,q,opt", CASES)
def test_analytical_matches_finite_diff(S, K, T, r, sigma, q, opt):
    g_analytical = bs_greeks(S, K, T, r, sigma, q, opt)
    g_fd = fd_greeks(bs_price, S, K, T, r, sigma, q, opt)

    # Loose tolerances: FD has O(h^2) truncation + roundoff.
    # Delta tolerance is governed by the 1% bump on S; truncation can run
    # to a few parts in 1e4 when |gamma''| is non-trivial.
    assert g_fd.delta == pytest.approx(g_analytical.delta, abs=5e-4)
    assert g_fd.gamma == pytest.approx(g_analytical.gamma, abs=1e-4)
    assert g_fd.vega == pytest.approx(g_analytical.vega, abs=1e-3)
    assert g_fd.theta == pytest.approx(g_analytical.theta, abs=1e-2)
    assert g_fd.rho == pytest.approx(g_analytical.rho, abs=1e-3)
