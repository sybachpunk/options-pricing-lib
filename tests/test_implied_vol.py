"""Implied vol round-trip."""
import pytest

from options_pricing import bs_price, implied_vol


@pytest.mark.parametrize("sigma_true", [0.10, 0.20, 0.35, 0.60, 1.20])
@pytest.mark.parametrize("opt", ["call", "put"])
def test_iv_round_trip(sigma_true, opt):
    S, K, T, r, q = 100.0, 105.0, 0.75, 0.04, 0.01
    price = bs_price(S, K, T, r, sigma_true, q, opt)
    iv = implied_vol(price, S, K, T, r, q, opt)
    assert iv == pytest.approx(sigma_true, abs=1e-6)


def test_iv_violates_bounds():
    # A call worth more than the underlying is impossible
    with pytest.raises(ValueError):
        implied_vol(200.0, 100.0, 100.0, 1.0, 0.05, 0.0, "call")
