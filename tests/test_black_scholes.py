"""Closed-form BSM correctness: known values, put-call parity, edge cases."""
import math

import pytest

from options_pricing import bs_price, bs_greeks


# Reference values from Hull, Options Futures and Other Derivatives, 11e
# (S=42, K=40, r=0.10, sigma=0.20, T=0.5, q=0): call = 4.7594, put = 0.8086
REFERENCE_CASES = [
    # (S, K, T, r, sigma, q, type, expected_price)
    (42.0, 40.0, 0.5, 0.10, 0.20, 0.0, "call", 4.7594),
    (42.0, 40.0, 0.5, 0.10, 0.20, 0.0, "put", 0.8086),
    (100.0, 100.0, 1.0, 0.05, 0.20, 0.0, "call", 10.4506),
    (100.0, 100.0, 1.0, 0.05, 0.20, 0.0, "put", 5.5735),
]


@pytest.mark.parametrize("S,K,T,r,sigma,q,opt,expected", REFERENCE_CASES)
def test_bs_known_values(S, K, T, r, sigma, q, opt, expected):
    price = bs_price(S, K, T, r, sigma, q, opt)
    assert price == pytest.approx(expected, abs=1e-3)


def test_put_call_parity():
    """C - P = S e^{-qT} - K e^{-rT}"""
    S, K, T, r, sigma, q = 100.0, 95.0, 1.0, 0.04, 0.25, 0.02
    c = bs_price(S, K, T, r, sigma, q, "call")
    p = bs_price(S, K, T, r, sigma, q, "put")
    rhs = S * math.exp(-q * T) - K * math.exp(-r * T)
    assert (c - p) == pytest.approx(rhs, abs=1e-10)


def test_intrinsic_at_expiry():
    assert bs_price(110.0, 100.0, 0.0, 0.05, 0.2, 0.0, "call") == pytest.approx(10.0)
    assert bs_price(90.0, 100.0, 0.0, 0.05, 0.2, 0.0, "put") == pytest.approx(10.0)
    assert bs_price(100.0, 100.0, 0.0, 0.05, 0.2, 0.0, "call") == pytest.approx(0.0)


def test_zero_vol_deterministic_limit():
    """With sigma = 0 the terminal price is the forward, so the option is the
    discounted payoff on F = S*exp((r-q)T) — moneyness is forward moneyness,
    not spot vs strike."""
    S, K, T, r, q = 100.0, 101.0, 1.0, 0.05, 0.0
    fwd = S * math.exp((r - q) * T)
    assert fwd > K  # spot is below strike but the forward is above it
    expected_call = math.exp(-r * T) * (fwd - K)
    assert bs_price(S, K, T, r, 0.0, q, "call") == pytest.approx(expected_call, abs=1e-10)
    # Put on a higher strike: forward is below it, so the put has value
    K_put = 110.0
    expected_put = math.exp(-r * T) * (K_put - fwd)
    assert bs_price(S, K_put, T, r, 0.0, q, "put") == pytest.approx(expected_put, abs=1e-10)
    # Zero-vol delta: discounted hedge ratio when in the money on the forward
    g = bs_greeks(S, K, T, r, 0.0, q, "call")
    assert g.delta == pytest.approx(math.exp(-q * T))
    assert g.gamma == 0.0 and g.vega == 0.0


def test_deep_itm_call_approaches_forward_minus_strike():
    """Deep ITM call ≈ S e^{-qT} - K e^{-rT}."""
    S, K, T, r, sigma, q = 200.0, 50.0, 1.0, 0.04, 0.20, 0.0
    c = bs_price(S, K, T, r, sigma, q, "call")
    expected = S * math.exp(-q * T) - K * math.exp(-r * T)
    assert c == pytest.approx(expected, rel=1e-4)


def test_greeks_signs():
    g = bs_greeks(100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    assert 0 < g.delta < 1
    assert g.gamma > 0
    assert g.vega > 0
    assert g.theta < 0  # long call decays
    assert g.rho > 0

    g_p = bs_greeks(100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "put")
    assert -1 < g_p.delta < 0
    assert g_p.gamma > 0
    assert g_p.vega > 0
    assert g_p.rho < 0


def test_call_put_gamma_vega_equal():
    """Gamma and vega are the same for puts and calls with same parameters."""
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0)
    gc = bs_greeks(*args, "call")
    gp = bs_greeks(*args, "put")
    assert gc.gamma == pytest.approx(gp.gamma)
    assert gc.vega == pytest.approx(gp.vega)


def test_call_put_delta_relation():
    """Delta_call - Delta_put = e^{-qT}"""
    S, K, T, r, sigma, q = 100.0, 100.0, 1.0, 0.05, 0.25, 0.02
    gc = bs_greeks(S, K, T, r, sigma, q, "call")
    gp = bs_greeks(S, K, T, r, sigma, q, "put")
    assert (gc.delta - gp.delta) == pytest.approx(math.exp(-q * T), abs=1e-10)
