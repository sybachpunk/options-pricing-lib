# `options_pricing` — module notes

The pure-Python reference implementation. Every other engine (C++, the tree, MC)
is validated against the closed form in `black_scholes.py`, which is the oracle.

## Module map

| File | What's in it | Key entry points |
|------|--------------|------------------|
| `black_scholes.py` | BSM closed form + analytical Greeks; a vectorized `bs_price_vec` for surfaces | `bs_price`, `bs_price_vec`, `bs_greeks`, `bs_d1_d2` |
| `binomial.py` | Cox-Ross-Rubinstein lattice, European + American; Greeks read off the tree | `crr_price`, `crr_greeks` |
| `monte_carlo.py` | European MC with antithetic + control variates; a convergence sweep helper | `mc_price`, `mc_convergence` |
| `greeks.py` | Generic finite-difference Greeks for *any* pricer (used to validate the closed form and to Greek the MC/exotic pricers) | `fd_greeks` |
| `implied_vol.py` | Brent-method IV solver with arbitrage-bound checks | `implied_vol` |
| `exotics.py` | Path-dependent payoffs via MC: arithmetic Asian (geometric-Asian control variate), barriers; geometric-Asian closed forms for both continuous (Kemna-Vorst) and discrete sampling — the discrete one is the CV reference | `asian_price`, `barrier_price`, `geometric_asian_price`, `geometric_asian_price_discrete` |
| `types.py` | Frozen dataclasses: `OptionSpec`, `Greeks`, `PricingResult` | — |

## Conventions (read before trusting a number)

- **Rates/vol are absolute, not percent.** `r=0.05` is 5%, `sigma=0.25` is 25%.
- **`q`** is a continuous dividend yield; set `q=0` for a non-dividend asset.
- **Greeks scaling:** vega and rho are per **1.0** of vol/rate (divide by 100 for
  per-1% quotes); theta is per **year** of calendar time and is **negative** for
  long options.
- **`option_type`** is the string `"call"` or `"put"` throughout — no enums, to keep
  the C++/HTTP boundaries trivial.

## Numerical gotchas

- **Tree gamma is read off step-2 nodes, never finite-differenced.** The tree price
  is not smooth in `S`; a second difference would alias node-oscillation noise into
  gamma. `crr_greeks` does the analytic node extraction.
- **Tree theta has no sign flip.** The central node two steps in sits at spot `S`,
  `2·dt` later in calendar time, so `(V(2dt) − V(0)) / (2dt)` *is* `∂P/∂t` (negative).
  A test pins this against BSM. (See repo README → "Numerical caveats".)
- **MC Greeks need a fixed `seed`** so bumped re-prices share random numbers; without
  it the bump signal drowns in Monte Carlo noise.
- **The Asian control variate uses the discrete-sampling closed form** with the same
  `n_steps` as the simulation. A control's expected value must be exact for the
  control as simulated; the continuous-averaging formula prices a different contract.
- **Antithetic standard errors are computed over pair averages** — each `(Z, −Z)`
  pair collapses to one observation, so the SE is a valid i.i.d. estimate that
  credits the variance reduction. This also means antithetic runs need ≥ 4 paths.
- **Zero-vol moneyness is forward moneyness.** As `σ → 0` (or `T → 0`) the price is
  the discounted payoff at `F = S·e^{(r−q)T}` — `F` vs `K`, not `S` vs `K`.
- **Barrier MC has discretization bias** (misses between-step crossings). Documented
  in `exotics.py`; mitigate with more steps or a Brownian bridge.

## Adding a new payoff

1. Implement it in Python first; add it to `__init__.py`'s `__all__`.
2. Add a consistency test (a relation that *must* hold — parity, a closed-form limit,
   or agreement with another method) rather than hard-coding a magic number.
3. If it's hot, port to `cpp/bindings.cpp` and add a parity test in
   `tests/test_cpp_engine.py`.
