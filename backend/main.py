"""
FastAPI app exposing the pricing library to the React frontend.

Run with:  uvicorn backend.main:app --reload --port 8000
"""
from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from options_pricing import (
    bs_price,
    bs_greeks,
    crr_price,
    crr_greeks,
    mc_price,
    fd_greeks,
    implied_vol,
    asian_price,
    barrier_price,
)
from options_pricing.monte_carlo import mc_convergence
from options_pricing.types import PricingResult

from .schemas import (
    AsianRequest,
    BarrierRequest,
    ConvergencePoint,
    ConvergenceRequest,
    ConvergenceResponse,
    GreeksResponse,
    ImpliedVolRequest,
    ImpliedVolResponse,
    PriceRequest,
    PriceResponse,
)


app = FastAPI(
    title="Options Pricing API",
    description="REST interface to a from-scratch options-pricing library "
                "(Black-Scholes-Merton, CRR binomial, Monte Carlo).",
    version="0.1.0",
)

# Vite dev server runs on 5173; allow any localhost origin for dev.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _greeks_to_response(g: Any) -> GreeksResponse:
    return GreeksResponse(
        delta=g.delta, gamma=g.gamma, vega=g.vega, theta=g.theta, rho=g.rho
    )


@app.get("/api/health")
def health() -> dict:
    from options_pricing import cpp_engine
    return {
        "status": "ok",
        "cpp_engine_loaded": cpp_engine is not None,
    }


@app.post("/api/price", response_model=PriceResponse)
def price_endpoint(req: PriceRequest) -> PriceResponse:
    t0 = time.perf_counter()

    args = (req.S, req.K, req.T, req.r, req.sigma, req.q, req.option_type)

    if req.method == "black_scholes":
        if req.american:
            raise HTTPException(400, "BSM closed form does not support American options.")
        price = bs_price(*args)
        greeks = bs_greeks(*args)
        result_meta: dict = {}
    elif req.method == "binomial":
        price = crr_price(*args, n_steps=req.n_steps, american=req.american)
        greeks = crr_greeks(*args, n_steps=req.n_steps, american=req.american)
        result_meta = {"n_steps": req.n_steps}
    elif req.method == "monte_carlo":
        if req.american:
            raise HTTPException(400, "Plain MC does not handle American exercise. Use binomial.")
        res = mc_price(
            *args,
            n_paths=req.n_paths,
            antithetic=req.antithetic,
            control_variate=req.control_variate,
            seed=req.seed,
            return_full=True,
        )
        assert isinstance(res, PricingResult)
        price = res.price
        # Greeks via finite differences over the MC pricer; reuse the seed so
        # the bumped re-prices use common random numbers (huge variance win).
        greeks = fd_greeks(
            mc_price, req.S, req.K, req.T, req.r, req.sigma, req.q, req.option_type,
            n_paths=req.n_paths, seed=req.seed, antithetic=req.antithetic,
            control_variate=req.control_variate, return_full=False,
        )
        result_meta = {"n_paths": req.n_paths, "std_error": res.std_error}
    else:
        raise HTTPException(400, f"Unknown method: {req.method}")

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return PriceResponse(
        price=price,
        method=req.method,
        elapsed_ms=elapsed_ms,
        greeks=_greeks_to_response(greeks),
        **result_meta,
    )


@app.post("/api/convergence", response_model=ConvergenceResponse)
def convergence_endpoint(req: ConvergenceRequest) -> ConvergenceResponse:
    bsm = bs_price(req.S, req.K, req.T, req.r, req.sigma, req.q, req.option_type)
    rows = mc_convergence(
        req.S, req.K, req.T, req.r, req.sigma, req.q, req.option_type,
        path_counts=sorted(req.path_counts),
        antithetic=req.antithetic,
        control_variate=req.control_variate,
        seed=req.seed,
    )
    return ConvergenceResponse(
        bsm_reference=bsm,
        points=[ConvergencePoint(**row) for row in rows],
    )


@app.post("/api/implied_vol", response_model=ImpliedVolResponse)
def iv_endpoint(req: ImpliedVolRequest) -> ImpliedVolResponse:
    t0 = time.perf_counter()
    try:
        iv = implied_vol(
            req.market_price, req.S, req.K, req.T, req.r, req.q, req.option_type
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return ImpliedVolResponse(
        implied_vol=iv,
        elapsed_ms=(time.perf_counter() - t0) * 1000.0,
    )


@app.post("/api/asian", response_model=PriceResponse)
def asian_endpoint(req: AsianRequest) -> PriceResponse:
    t0 = time.perf_counter()
    res = asian_price(
        req.S, req.K, req.T, req.r, req.sigma, req.q, req.option_type,
        n_paths=req.n_paths, n_steps=req.n_steps,
        control_variate=req.control_variate, seed=req.seed,
    )
    return PriceResponse(
        price=res.price,
        method="monte_carlo_asian",
        std_error=res.std_error,
        n_paths=res.n_paths,
        n_steps=res.n_steps,
        elapsed_ms=(time.perf_counter() - t0) * 1000.0,
    )


@app.post("/api/barrier", response_model=PriceResponse)
def barrier_endpoint(req: BarrierRequest) -> PriceResponse:
    t0 = time.perf_counter()
    try:
        res = barrier_price(
            req.S, req.K, req.T, req.r, req.sigma, req.barrier, req.kind,
            req.q, req.option_type,
            n_paths=req.n_paths, n_steps=req.n_steps, seed=req.seed,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    return PriceResponse(
        price=res.price,
        method=f"monte_carlo_barrier:{req.kind}",
        std_error=res.std_error,
        n_paths=res.n_paths,
        n_steps=res.n_steps,
        elapsed_ms=(time.perf_counter() - t0) * 1000.0,
    )
