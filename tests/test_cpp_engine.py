"""C++ engine should match the Python reference (when the extension is built)."""
import pytest

import options_pricing as op

cpp = op.cpp_engine
pytestmark = pytest.mark.skipif(cpp is None, reason="C++ extension not built")


def test_cpp_bs_matches_python():
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    py_price = op.bs_price(*args)
    cpp_price = cpp.bs_price(*args)
    assert cpp_price == pytest.approx(py_price, abs=1e-10)


def test_cpp_crr_matches_python():
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    py = op.crr_price(*args, n_steps=500)
    c = cpp.crr_price(*args, n_steps=500, american=False)
    assert c == pytest.approx(py, abs=1e-10)


def test_cpp_mc_matches_bsm_within_se():
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    bsm = op.bs_price(*args)
    res = cpp.mc_price(*args, n_paths=200_000, antithetic=True,
                       control_variate=True, seed=42)
    assert abs(res["price"] - bsm) < 3 * res["std_error"] + 0.02
    # Both engines report the requested total path count
    assert res["n_paths"] == 200_000
    py_res = op.mc_price(*args, n_paths=200_000, seed=42, return_full=True)
    assert py_res.n_paths == 200_000


def test_cpp_greeks_match():
    args = (100.0, 100.0, 1.0, 0.05, 0.25, 0.0, "call")
    py_g = op.bs_greeks(*args)
    c_g = cpp.bs_greeks(*args)
    assert c_g["delta"] == pytest.approx(py_g.delta, abs=1e-10)
    assert c_g["gamma"] == pytest.approx(py_g.gamma, abs=1e-10)
    assert c_g["vega"]  == pytest.approx(py_g.vega,  abs=1e-10)
    assert c_g["theta"] == pytest.approx(py_g.theta, abs=1e-10)
    assert c_g["rho"]   == pytest.approx(py_g.rho,   abs=1e-10)
