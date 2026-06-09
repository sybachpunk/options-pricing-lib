"""Pydantic request/response schemas for the pricing API."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict


OptionType = Literal["call", "put"]
Method = Literal["black_scholes", "binomial", "monte_carlo"]


class OptionInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    S: float = Field(gt=0, description="Spot price")
    K: float = Field(gt=0, description="Strike price")
    T: float = Field(gt=0, le=50, description="Time to expiry in years")
    r: float = Field(ge=-0.5, le=1.0, description="Risk-free rate (continuous)")
    sigma: float = Field(gt=0, le=5.0, description="Volatility (annualized)")
    q: float = Field(default=0.0, ge=0, le=1.0, description="Continuous dividend yield")
    option_type: OptionType = "call"


class PriceRequest(OptionInputs):
    method: Method = "black_scholes"
    american: bool = False           # only meaningful for binomial
    n_steps: int = Field(default=500, ge=10, le=10_000)
    n_paths: int = Field(default=100_000, ge=100, le=2_000_000)
    antithetic: bool = True
    control_variate: bool = True
    seed: Optional[int] = 42


class GreeksResponse(BaseModel):
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class PriceResponse(BaseModel):
    price: float
    method: str
    std_error: Optional[float] = None
    n_paths: Optional[int] = None
    n_steps: Optional[int] = None
    elapsed_ms: float
    greeks: Optional[GreeksResponse] = None


class ConvergenceRequest(OptionInputs):
    path_counts: list[int] = Field(
        default=[1_000, 5_000, 20_000, 100_000, 500_000],
        max_length=20,
    )
    antithetic: bool = True
    control_variate: bool = True
    seed: int = 42


class ConvergencePoint(BaseModel):
    n_paths: int
    price: float
    std_error: float


class ConvergenceResponse(BaseModel):
    bsm_reference: float
    points: list[ConvergencePoint]


class ImpliedVolRequest(BaseModel):
    market_price: float = Field(gt=0)
    S: float = Field(gt=0)
    K: float = Field(gt=0)
    T: float = Field(gt=0)
    r: float
    q: float = 0.0
    option_type: OptionType = "call"


class ImpliedVolResponse(BaseModel):
    implied_vol: float
    elapsed_ms: float


class BarrierRequest(OptionInputs):
    barrier: float = Field(gt=0)
    kind: Literal["up-and-out", "down-and-out", "up-and-in", "down-and-in"]
    n_paths: int = Field(default=100_000, ge=100, le=2_000_000)
    n_steps: int = Field(default=252, ge=10, le=5_000)
    seed: int = 42


class AsianRequest(OptionInputs):
    n_paths: int = Field(default=100_000, ge=100, le=2_000_000)
    n_steps: int = Field(default=100, ge=10, le=5_000)
    control_variate: bool = True
    seed: int = 42
