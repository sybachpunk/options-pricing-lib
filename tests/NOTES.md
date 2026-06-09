# Tests — notes

The testing philosophy here is **consistency relations, not magic numbers**. Wherever
possible a test asserts a relation that *must* hold under no-arbitrage or in a limit —
the same kind of invariant a production pricing desk monitors. Those catch far more
bugs than hard-coded expected values, and they double as a readable spec of the API.

Run everything: `pytest -v` (the C++ parity tests skip unless the engine is built).

## What each file pins down

| File | The invariants it checks |
|------|--------------------------|
| `test_black_scholes.py` | Known Hull values; **put-call parity**; intrinsic at expiry; **zero-vol limit = discounted payoff on the forward**; deep-ITM → forward−strike; Greek signs; `Δ_call − Δ_put = e^(−qT)`; gamma/vega equal for call & put |
| `test_binomial.py` | CRR → BSM as `n→∞`; American call (no div) == European; American put premium > 0; **CRR Greeks match BSM** + **theta is negative** |
| `test_monte_carlo.py` | MC within 3σ of BSM; std-error shrinks ~`1/√N`; antithetic and control variate each reduce variance; antithetic requires ≥ 2 pairs |
| `test_greeks.py` | Analytical BSM Greeks == finite-difference Greeks across moneyness/maturity |
| `test_implied_vol.py` | IV round-trips for σ ∈ [10%, 120%]; raises when the price violates arbitrage bounds |
| `test_exotics.py` | Asian cheaper than vanilla (averaging dampens vol); continuous < discrete < vanilla geometric ordering with monotone convergence; **discrete geometric closed form == direct simulation** (what qualifies it as a control); **CV estimator == plain MC** (controls shrink error bars, never move the target); **barrier in/out parity**: knock-in + knock-out == vanilla |
| `test_cpp_engine.py` | C++ matches Python to ~1e-10 (BSM, CRR) and within std-error (MC); both engines report the same `n_paths` convention; skips if `cpp_engine is None` |

## Why some tolerances look loose

- **CRR vs BSM** uses an `≈ 3/n` envelope — the `O(1/n)` constant is largest at-the-money.
- **MC vs BSM** is checked at 3 standard errors (~99.7%), not equality — it's a random estimator.
- **FD delta** allows `5e-4`: the 1%-of-spot bump carries `O(h²)` truncation error.
- **Barrier parity** allows `~3·(SE_in + SE_out)`: it's the sum of two noisy MC estimates.

These bands are wide enough to never flake, tight enough that a real regression
trips them.

## When you add a test

Prefer an invariant. If you must assert a number, source it (Hull, a closed form,
or another method in this repo) and say so in a comment.
