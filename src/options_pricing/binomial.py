"""
Cox-Ross-Rubinstein binomial tree.

Method:
    Per step of length dt = T/n:
        u = exp(sigma * sqrt(dt))   (up factor)
        d = 1/u                     (down factor)
        p = (exp((r - q)*dt) - d) / (u - d)   (risk-neutral up probability)

    Build terminal asset prices, compute payoffs, then backward-induct:
        V_i = exp(-r*dt) * (p * V_up + (1-p) * V_down)

    For American options, at each interior node take
        V_i = max(intrinsic(S_i), continuation_value)

Why this works:
    The discrete tree replicates the lognormal moments of the GBM as n -> inf,
    so prices converge to BSM (O(1/n) error). Trees naturally handle
    early-exercise by checking intrinsic at every step — the price of an
    American call/put falls out of the recursion.
"""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np

from .types import Greeks, OptionType


def _crr_params(T: float, r: float, sigma: float, q: float, n: int) -> Tuple[float, float, float, float]:
    dt = T / n
    u = math.exp(sigma * math.sqrt(dt))
    d = 1.0 / u
    p = (math.exp((r - q) * dt) - d) / (u - d)
    return dt, u, d, p


def crr_price(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: OptionType = "call",
    n_steps: int = 500,
    american: bool = False,
) -> float:
    """Price a European or American option via the CRR binomial tree."""
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")
    if T <= 0:
        intrinsic = max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
        return float(intrinsic)

    dt, u, d, p = _crr_params(T, r, sigma, q, n_steps)
    disc = math.exp(-r * dt)

    # Probability outside (0,1) signals an arbitrage / inconsistent setup
    # (most often: sigma too small relative to (r-q)*sqrt(dt)).
    if not (0.0 <= p <= 1.0):
        raise ValueError(
            f"CRR risk-neutral probability p={p:.4f} is outside [0,1]. "
            "Reduce n_steps or check inputs."
        )

    j = np.arange(n_steps + 1)
    # Terminal asset prices: S_j = S * u^(n-j) * d^j
    ST = S * (u ** (n_steps - j)) * (d**j)

    if option_type == "call":
        values = np.maximum(ST - K, 0.0)
    else:
        values = np.maximum(K - ST, 0.0)

    for step in range(n_steps - 1, -1, -1):
        values = disc * (p * values[:-1] + (1 - p) * values[1:])
        if american:
            # Asset prices at this step
            jj = np.arange(step + 1)
            S_step = S * (u ** (step - jj)) * (d**jj)
            if option_type == "call":
                intrinsic = np.maximum(S_step - K, 0.0)
            else:
                intrinsic = np.maximum(K - S_step, 0.0)
            values = np.maximum(values, intrinsic)

    return float(values[0])


def crr_greeks(
    S: float,
    K: float,
    T: float,
    r: float,
    sigma: float,
    q: float = 0.0,
    option_type: OptionType = "call",
    n_steps: int = 500,
    american: bool = False,
) -> Greeks:
    """
    Greeks from a single binomial tree.

    Delta and gamma are read directly off the tree (nodes at steps 1 and 2),
    avoiding a separate finite-difference shock. Theta uses node values at
    step 2 (advancing time by 2*dt). Vega and rho use bumped-tree
    finite differences since they aren't natural by-products of the recursion.
    """
    if n_steps < 4:
        raise ValueError("n_steps must be >= 4 for tree-based Greeks")

    dt, u, d, p = _crr_params(T, r, sigma, q, n_steps)
    disc = math.exp(-r * dt)

    j = np.arange(n_steps + 1)
    ST = S * (u ** (n_steps - j)) * (d**j)
    if option_type == "call":
        values = np.maximum(ST - K, 0.0)
    else:
        values = np.maximum(K - ST, 0.0)

    # Backward induction, saving values at step 2 and step 1 for Greeks
    v_step2 = None
    v_step1 = None
    for step in range(n_steps - 1, -1, -1):
        values = disc * (p * values[:-1] + (1 - p) * values[1:])
        if american:
            jj = np.arange(step + 1)
            S_step = S * (u ** (step - jj)) * (d**jj)
            if option_type == "call":
                intrinsic = np.maximum(S_step - K, 0.0)
            else:
                intrinsic = np.maximum(K - S_step, 0.0)
            values = np.maximum(values, intrinsic)
        if step == 2:
            v_step2 = values.copy()
        elif step == 1:
            v_step1 = values.copy()

    price = float(values[0])

    # Delta from step 1 nodes
    S_up = S * u
    S_dn = S * d
    delta = (v_step1[0] - v_step1[1]) / (S_up - S_dn)

    # Gamma from step 2 nodes (three asset prices)
    S_uu = S * u * u
    S_ud = S
    S_dd = S * d * d
    delta_up = (v_step2[0] - v_step2[1]) / (S_uu - S_ud)
    delta_dn = (v_step2[1] - v_step2[2]) / (S_ud - S_dd)
    gamma = (delta_up - delta_dn) / (0.5 * (S_uu - S_dd))

    # Theta from step 2 middle node. Because the tree recombines (u*d = 1),
    # the central node at step 2 sits at the same spot S but 2*dt later in
    # CALENDAR time. Theta is the calendar-time derivative dV/dt, so it is
    # simply (V(t=2dt) - V(t=0)) / (2dt) — already negative for a long option
    # as its time value decays. (No sign flip: dV/dt is the convention, and
    # advancing calendar time is what the forward node represents.)
    theta = (v_step2[1] - price) / (2 * dt)

    # Bump-and-reprice for vega, rho (use modest bump so the surrounding tree
    # parameters stay well-behaved)
    h_sigma = 0.01
    h_r = 1e-4
    p_up = crr_price(S, K, T, r, sigma + h_sigma, q, option_type, n_steps, american)
    p_dn = crr_price(S, K, T, r, sigma - h_sigma, q, option_type, n_steps, american)
    vega = (p_up - p_dn) / (2 * h_sigma)

    p_up = crr_price(S, K, T, r + h_r, sigma, q, option_type, n_steps, american)
    p_dn = crr_price(S, K, T, r - h_r, sigma, q, option_type, n_steps, american)
    rho = (p_up - p_dn) / (2 * h_r)

    return Greeks(
        delta=float(delta),
        gamma=float(gamma),
        vega=float(vega),
        theta=float(theta),
        rho=float(rho),
    )
