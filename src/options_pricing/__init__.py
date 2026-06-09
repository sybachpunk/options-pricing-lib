"""
options_pricing — from-scratch derivatives pricing library.

Public API:
    bs_price, bs_greeks               — Black-Scholes-Merton closed form
    crr_price, crr_greeks             — Cox-Ross-Rubinstein binomial tree
    mc_price                          — Monte Carlo with antithetic + control variates
    fd_greeks                         — Finite-difference Greeks (works on any pricer)
    implied_vol                       — Brent's-method IV solver
    asian_price, barrier_price        — Exotic options via Monte Carlo

A C++ engine is exposed as `options_pricing.cpp_engine` when the extension
module is built; otherwise that attribute is None.
"""
from .types import OptionSpec, Greeks, PricingResult
from .black_scholes import bs_price, bs_greeks, bs_d1_d2, bs_price_vec
from .binomial import crr_price, crr_greeks
from .monte_carlo import mc_price
from .greeks import fd_greeks
from .implied_vol import implied_vol
from .exotics import (
    asian_price,
    barrier_price,
    geometric_asian_price,
    geometric_asian_price_discrete,
)

try:
    from . import _cpp_engine as cpp_engine  # type: ignore[attr-defined]
except ImportError:
    cpp_engine = None  # type: ignore[assignment]

__all__ = [
    "OptionSpec",
    "Greeks",
    "PricingResult",
    "bs_price",
    "bs_greeks",
    "bs_d1_d2",
    "bs_price_vec",
    "crr_price",
    "crr_greeks",
    "mc_price",
    "fd_greeks",
    "implied_vol",
    "asian_price",
    "barrier_price",
    "geometric_asian_price",
    "geometric_asian_price_discrete",
    "cpp_engine",
]

__version__ = "0.1.0"
