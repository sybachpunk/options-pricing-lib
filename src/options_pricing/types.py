"""Shared dataclasses for option specs, Greeks, and pricing results."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal, Optional

OptionType = Literal["call", "put"]


@dataclass(frozen=True)
class OptionSpec:
    S: float
    K: float
    T: float
    r: float
    sigma: float
    q: float = 0.0
    option_type: OptionType = "call"

    def __post_init__(self) -> None:
        if self.S <= 0 or self.K <= 0:
            raise ValueError("S and K must be positive")
        if self.T < 0:
            raise ValueError("T must be non-negative")
        if self.sigma < 0:
            raise ValueError("sigma must be non-negative")
        if self.option_type not in ("call", "put"):
            raise ValueError("option_type must be 'call' or 'put'")

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Greeks:
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class PricingResult:
    price: float
    method: str
    std_error: Optional[float] = None
    n_paths: Optional[int] = None
    n_steps: Optional[int] = None
    elapsed_ms: Optional[float] = None
    extras: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)
