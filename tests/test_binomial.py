"""CRR binomial: convergence to BSM, American >= European, parity, Greeks."""
import pytest

from options_pricing import bs_price, bs_greeks, crr_price, crr_greeks


def test_crr_converges_to_bsm_european_call():
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    bsm = bs_price(*args)
    # CRR error scales as O(1/n) with a constant that depends on moneyness.
    # The constant is largest near ATM; ~3/n is a safe envelope.
    for n in [50, 200, 1000]:
        p = crr_price(*args, n_steps=n)
        assert p == pytest.approx(bsm, abs=3.0 / n + 1e-3)
    # Tightest tolerance at n=1000
    assert crr_price(*args, n_steps=1000) == pytest.approx(bsm, abs=0.02)


def test_crr_converges_to_bsm_european_put():
    args = (100.0, 110.0, 1.0, 0.03, 0.30, 0.02, "put")
    bsm = bs_price(*args)
    assert crr_price(*args, n_steps=1000) == pytest.approx(bsm, abs=0.03)


def test_american_call_no_dividend_equals_european():
    """Classic result: it's never optimal to early-exercise an American call
    on a non-dividend asset (Merton). So American == European."""
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    eu = crr_price(*args, n_steps=500, american=False)
    am = crr_price(*args, n_steps=500, american=True)
    assert am == pytest.approx(eu, abs=1e-6)


def test_american_put_premium_over_european():
    """American put on a non-dividend asset SHOULD have an early-exercise premium."""
    args = (100.0, 110.0, 1.0, 0.05, 0.25, 0.0, "put")
    eu = crr_price(*args, n_steps=500, american=False)
    am = crr_price(*args, n_steps=500, american=True)
    assert am > eu
    assert (am - eu) > 0.1  # premium should be material


def test_crr_intrinsic_at_expiry():
    # T=0 corner: tree should still produce intrinsic
    assert crr_price(110, 100, 0.0, 0.05, 0.25, 0.0, "call", n_steps=10) == pytest.approx(10.0)


# --- Tree-based Greeks should converge to the closed-form BSM Greeks for
#     European options. This is the cross-check that catches a sign error or
#     a mis-indexed node in crr_greeks. ---
GREEK_CASES = [
    (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call"),
    (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "put"),
    (100.0, 110.0, 0.5, 0.03, 0.20, 0.02, "call"),
    (100.0, 90.0, 2.0, 0.04, 0.30, 0.01, "put"),
]


@pytest.mark.parametrize("S,K,T,r,sigma,q,opt", GREEK_CASES)
def test_crr_greeks_match_bsm_european(S, K, T, r, sigma, q, opt):
    bs = bs_greeks(S, K, T, r, sigma, q, opt)
    tree = crr_greeks(S, K, T, r, sigma, q, opt, n_steps=600)

    # Delta/gamma read straight off the lattice — tight agreement.
    assert tree.delta == pytest.approx(bs.delta, abs=2e-3)
    assert tree.gamma == pytest.approx(bs.gamma, abs=2e-3)
    # Vega/rho are bumped-tree finite differences — looser.
    assert tree.vega == pytest.approx(bs.vega, abs=0.3)
    assert tree.rho == pytest.approx(bs.rho, abs=0.3)
    # Theta must match in both sign and magnitude — a sign convention slip
    # here is exactly what this cross-check exists to catch.
    assert tree.theta == pytest.approx(bs.theta, abs=0.3)


@pytest.mark.parametrize("opt", ["call", "put"])
def test_crr_theta_is_negative_for_long_options(opt):
    """A long vanilla option loses time value as expiry approaches → theta < 0."""
    g = crr_greeks(100.0, 100.0, 1.0, 0.05, 0.25, 0.0, opt, n_steps=400)
    assert g.theta < 0
