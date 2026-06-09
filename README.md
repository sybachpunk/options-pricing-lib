# Options Pricing Library

An implementation of the three canonical European option pricing methods:

- **Black-Scholes-Merton** closed form with analytical Greeks
- **Cox-Ross-Rubinstein binomial tree** with European and American exercise
- **Monte Carlo simulation** with antithetic and control variates
- **All five Greeks** computed two ways (analytical *and* finite-difference) and cross-validated against each other
- **Exotic options**: arithmetic Asian (with geometric Asian as control variate), knock-in/knock-out barriers
- **Implied volatility solver** (Brent's method)
- **C++ port via pybind11** for a real speed comparison
- **FastAPI + React fullstack app** for interactive exploration
- **Jupyter notebook** with convergence plots and a written analysis of when to use which method

---

## Quick start

### 1. Prerequisites
- Python ≥ 3.10
- A C++17 compiler (MSVC on Windows, gcc/clang elsewhere) — *optional, only needed for the C++ engine and its benchmark*
- Node ≥ 18 — *optional, only needed for the React frontend*

### 2. Install the Python library

```bash
# Create a venv and install everything in editable mode
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # macOS / Linux

pip install -e ".[dev,api]"
```

The `[dev]` extra pulls pytest, matplotlib, pandas, and jupyter. The `[api]` extra adds FastAPI + uvicorn.

**Building the C++ engine (optional).** It's opt-in via an environment variable so users without a C++ toolchain aren't blocked. With a working compiler (MSVC Build Tools on Windows, gcc/clang elsewhere):

```powershell
# Windows PowerShell
$env:OPTIONS_PRICING_BUILD_CPP="1"
pip install -e ".[dev,api]"
```

```bash
# macOS / Linux
OPTIONS_PRICING_BUILD_CPP=1 pip install -e ".[dev,api]"
```

Without the env var, the Python implementation is used everywhere and `options_pricing.cpp_engine` is `None`. The four C++ tests in `tests/test_cpp_engine.py` skip automatically.

### 3. Run the tests

```bash
pytest -v
```

The full suite should pass (the C++ engine parity tests skip automatically unless you built the native engine). Coverage spans:
- Closed-form BSM correctness vs. published Hull values
- Put-call parity (model-free arbitrage)
- Zero-volatility deterministic limit (option = discounted payoff on the forward)
- CRR convergence to BSM as `n → ∞`
- American put premium > 0; American call on non-dividend stock == European
- **CRR-tree Greeks match closed-form BSM Greeks** (delta/gamma/vega/theta/rho), plus an explicit guard that theta is negative for long options
- MC standard error shrinks like `1/√N`
- Antithetic and control variate each reduce variance
- **Asian control-variate estimator agrees with plain MC** (a control variate may only shrink the error bar, never move the target), and the discrete geometric closed form matches direct simulation
- Analytical Greeks match finite differences across moneyness and time-to-expiry
- Implied vol round-trips for vols spanning 10% – 120%
- Barrier in/out parity: knock-out + knock-in == vanilla
- C++ engine matches the Python reference to machine precision (when built)

> The suite runs from a fresh clone with only `numpy`, `scipy`, and `pytest` installed — `conftest.py` puts `src/` on the path so you don't strictly need `pip install -e .` first.

### 4. Open the notebook

```bash
jupyter notebook notebooks/pricing_showcase.ipynb
```

This is the **main portfolio deliverable**. It walks through every method with plots, runs the cross-validation, produces the accuracy comparison table, and benchmarks Python vs. C++.

### 5. Run the fullstack app (optional)

In one terminal:

```bash
uvicorn backend.main:app --reload --port 8000
```

In another:

```bash
cd frontend
npm install
npm run dev      # opens http://localhost:5173
```

The frontend proxies `/api/*` to the FastAPI backend. You get a pricer form, real-time Greeks, an MC convergence plot, a payoff diagram, and a side-by-side method comparison.

---

## Project layout

```
options-pricing-lib/
├── src/options_pricing/      Python library (the reference implementation)
│   ├── black_scholes.py        closed form + analytical Greeks
│   ├── binomial.py             Cox-Ross-Rubinstein tree
│   ├── monte_carlo.py          MC + antithetic + control variates
│   ├── greeks.py               finite-difference Greeks
│   ├── implied_vol.py          Brent-method IV solver
│   ├── exotics.py              Asian, barrier, geometric-Asian closed form
│   └── types.py                shared dataclasses
├── cpp/
│   ├── bindings.cpp            C++ engine with pybind11 bindings
│   └── CMakeLists.txt          standalone CMake build (setup.py is the primary path)
├── tests/                    pytest suite — read these to understand the API
│   └── NOTES.md                what each test file validates, and why
├── notebooks/
│   └── pricing_showcase.ipynb  the main deliverable
├── backend/                  FastAPI app exposing the engine over HTTP
│   └── NOTES.md                endpoint map + how Greeks are computed per method
├── frontend/                 React + Vite UI
│   └── NOTES.md                component map + dev-proxy setup
├── .github/workflows/ci.yml  CI: pure-Python matrix + a job that builds the C++ engine
├── conftest.py               puts src/ on sys.path so pytest runs from a clean clone
├── setup.py                  builds the C++ extension via pybind11.setup_helpers
├── LICENSE                   MIT
└── pyproject.toml            project metadata + dependencies
```

Most directories carry a short `NOTES.md` orienting you to what's inside and flagging
the numerical gotchas worth knowing before you trust a number.

---

## The math, briefly

### Black-Scholes-Merton

Under the risk-neutral measure ℚ, the asset follows geometric Brownian motion:

$$dS = (r - q)\,S\,dt + \sigma\,S\,dW$$

so log-S is normal at expiry. Pricing a European call reduces to the integral of `max(S_T − K, 0)` against this lognormal, discounted at `e^(−rT)`. Closed form:

$$C = S e^{-qT} N(d_1) - K e^{-rT} N(d_2), \quad d_{1,2} = \frac{\log(S/K) + (r - q \pm \sigma^2/2) T}{\sigma\sqrt T}$$

**Put-call parity** is a model-free relation (no GBM assumption needed):

$$C - P = S e^{-qT} - K e^{-rT}$$

If parity is violated in the market, you arbitrage it: hold long call + short put = synthetic forward.

### Cox-Ross-Rubinstein binomial tree

Per step of length `dt = T/n`:
- `u = exp(σ√dt)` is the up factor
- `d = 1/u` is the down factor
- `p = (exp((r-q)dt) − d) / (u − d)` is the risk-neutral up probability

Build a recombining lattice of asset prices, set terminal payoffs at the leaves, then backward-induct:

$$V_i = e^{-r\,dt}\bigl(p \cdot V_{\text{up}} + (1-p) \cdot V_{\text{down}}\bigr)$$

For **American options**, at every interior node take `max(intrinsic, continuation)`. The tree's discrete moments converge to those of GBM as `n → ∞`, so the price converges to BSM at `O(1/n)`.

### Monte Carlo

Sample terminal asset prices under the risk-neutral measure:

$$S_T = S \exp\bigl((r - q - \sigma^2/2) T + \sigma\sqrt T\,Z\bigr), \quad Z \sim \mathcal{N}(0,1)$$

Average `e^(−rT) · payoff(S_T)` over `N` samples. By the CLT, the estimator's standard error is `σ_payoff / √N` — convergence is `O(1/√N)`. **This is the key MC fact**: getting one more decimal place of accuracy requires 100× the samples.

Variance reduction lowers the *constant in front* of `1/√N` but does not change the rate:

- **Antithetic variates**: pair each `Z` with `−Z`. For monotone payoffs this gives negatively-correlated estimates and lower variance than 2N independent samples.
- **Control variates**: subtract `β(X − E[X])` from the payoff, where `X` is a related quantity with known mean. We use `X = e^(−rT)·S_T`, whose expectation is `S·e^(−qT)`. `β` is estimated from the sample covariance.

For Asian and barrier options, where there's no closed form and the payoff depends on the path, MC is the only practical choice. For arithmetic Asians we use the geometric Asian (closed form: Kemna-Vorst) as a control — the two payoffs are >99% correlated, so the variance reduction is dramatic.

### The five Greeks

Each is a partial derivative of the option price:

| Greek | Math       | Meaning                                            |
|-------|------------|----------------------------------------------------|
| Δ     | ∂P/∂S      | rate of change in price per unit change in spot    |
| Γ     | ∂²P/∂S²    | rate of change of delta — measures gamma risk      |
| ν     | ∂P/∂σ      | vega — sensitivity to volatility                   |
| Θ     | −∂P/∂T     | theta — calendar-time decay (negative for long opts) |
| ρ     | ∂P/∂r      | rho — sensitivity to interest rate                 |

All five have closed forms under BSM. We also compute them by finite-differencing the pricer:

$$\frac{\partial P}{\partial x} \approx \frac{P(x+h) - P(x-h)}{2h}$$

This is `O(h²)` accurate. The tests cross-validate the two: any mismatch indicates a bug. For Monte Carlo pricers you must use the same random seed for both bumps (*common random numbers*) — otherwise the noise dominates the bump signal.

---

## Numerical caveats & conventions

The gotchas that bite you in practice — read these before you trust a Greek or a price.

- **Theta sign convention.** Theta here is `∂P/∂t` (calendar time), so it is **negative** for long vanilla options — they bleed time value as expiry approaches. The binomial `crr_greeks` reads theta off the central node two steps into the tree (which sits at the same spot `S` but `2·dt` later), giving the calendar-time derivative directly with no sign flip. A test asserts the tree theta both matches BSM and is negative.

- **A control variate's mean must be exact for the control *as simulated*.** The arithmetic-Asian MC averages over `n_steps` discrete dates, so its control uses the discrete-sampling geometric closed form (`geometric_asian_price_discrete`) with the same observation count. The continuous-averaging Kemna-Vorst formula prices a different contract — its mean differs by ~0.13 on an ATM 1y call at 50 observations, which would shift the estimate while the error bar stayed tiny. A test pins the CV estimator to plain MC: variance reduction may shrink the error bar, never move the target.

- **Zero-volatility limit is the forward, not spot-vs-strike.** As `σ → 0` the terminal distribution collapses onto the forward `F = S·e^((r−q)T)`, so moneyness is decided by `F` vs `K`. A spot-below-strike call can still be solidly in the money on the forward.

- **Tree Greeks vs. finite-difference Greeks.** Delta and gamma are read straight off the lattice nodes (steps 1 and 2), which is accurate and cheap. Do **not** finite-difference the binomial price to get gamma: the tree price is *not smooth* in `S` (the strike lands at different relative positions between nodes as you bump `S`), so a second difference picks up node-oscillation noise and can be off by 2×. The library's tree gamma avoids this; only `fd_greeks` applied to the tree is noisy, and we use the analytic node extraction instead.

- **Monte Carlo Greeks are noisy.** Bump-and-revalue Greeks on an MC pricer are only usable with **common random numbers** (same seed for both bumps). Even then, gamma (a second difference) is the hardest to estimate. For production you'd reach for pathwise or likelihood-ratio estimators.

- **Discrete barrier monitoring is biased.** The barrier MC checks the breach condition only at the simulated time steps, so it can miss a crossing *between* observations. This biases knock-out prices high and knock-in prices low. Mitigate with more steps (≥ 250/yr) or a Brownian-bridge correction (not implemented — documented in `exotics.py`).

- **CRR risk-neutral probability can leave [0,1].** If `σ` is tiny relative to `(r−q)·√dt`, the up-probability `p` falls outside `[0,1]` and the tree is arbitrageable. The code raises rather than returning a garbage price.

---

## Learning points

Things I would have told myself at the start:

### On the math

- **The risk-neutral measure is a calculation device, not a real-world probability.** You're not predicting what S will do; you're computing the price that prevents arbitrage. Real-world drift (`μ`) never appears in BSM — only the risk-free rate `r`. That's not because nobody cares about `μ`, it's because the replication argument cancels it.

- **Greeks intuition before formulas.** Internalize *delta is a hedge ratio* before you memorize `e^(−qT) N(d_1)`. When someone asks "what's the delta of an at-the-money call?" your instinct should be "about 0.5" — not "let me look up the formula".

- **Put-call parity is more useful than you'd guess.** It lets you spot-check pricer output, derive put prices from call prices, and back out implied dividends. It holds under any no-arbitrage model — not just BSM.

- **The volatility smile is the market telling you BSM is wrong.** Real options aren't priced with a single σ. The smile/skew encodes fat tails, jumps, and stochastic vol that the lognormal model doesn't capture. People still use BSM because it's the *language* — they quote in implied vol, then use richer models internally.

### On the implementation

- **Vectorize aggressively in NumPy.** A binomial tree written with a Python `for` loop over nodes is 100× slower than one that processes a layer of nodes as a single array operation. Same for MC: never loop over paths in Python.

- **Set random seeds explicitly.** For tests, for finite-difference Greeks of an MC pricer, for any reproducible result. The default RNG state is not your friend.

- **Use common random numbers for MC Greeks.** Re-using the seed across the `x+h` and `x−h` evaluations is the difference between a usable estimate and pure noise. The bumped paths should be *the same paths*, just driven by a slightly different parameter.

- **Tests at the boundary of correctness.** Put-call parity, in/out barrier parity, BSM-vs-CRR limit, analytical-vs-FD Greeks — these aren't just unit tests, they're *consistency checks that real pricing systems run in production*. Get used to thinking in terms of relations that *must* hold.

- **A control variate is free variance reduction whenever it's available.** If you have a closed form for a related payoff, use it — the geometric-Asian control cuts the arithmetic Asian's standard error by 10×+. The discipline that comes with it: the control's expected value must be exact for the control *as simulated* (matching observation dates, discrete vs continuous averaging), or the estimator inherits the mismatch with a misleadingly small error bar.

### On the engineering

- **Closed-form first, then numerical methods.** The closed form is the oracle. Every other method gets validated against it on cases where both apply. If your tree disagrees with BSM at `n = 5000` by more than `0.01`, your tree has a bug — not BSM.

- **Two implementations of the same thing find more bugs than one.** The Python and C++ engines exist as much for cross-validation as for the speed benchmark. If they disagree, one of them is wrong, and figuring out which sharpens your understanding.

- **`pybind11` is the easiest path from C++ to Python.** Don't use ctypes, don't write raw CPython extensions. `pybind11.setup_helpers.Pybind11Extension` integrates with setuptools in five lines.

- **FastAPI + React is overkill for a notebook project, but it's the portfolio piece.** A working web app demonstrates that you can ship something end-to-end. The pricing math is the same code; the API and UI just expose it.

- **Don't optimize before you're correct.** Get the algorithms right with simple, slow NumPy code first. Profile. Then move the hot paths to C++ if and only if you actually need to.

---

## References

- Hull, *Options, Futures, and Other Derivatives* — the standard reference, undergraduate level. Reference values for the BSM tests come from here.
- Wilmott, *Paul Wilmott on Quantitative Finance* — three volumes, deeper and more numerical-methods-focused than Hull.
- Glasserman, *Monte Carlo Methods in Financial Engineering* — definitive on MC, including variance reduction, Greeks, and the Longstaff-Schwartz method for American MC.
- Shreve, *Stochastic Calculus for Finance II* — for the measure-theoretic foundations.
- Kemna & Vorst (1990), *A pricing method for options based on average asset values* — the geometric Asian closed form.

## License

MIT — see [LICENSE](LICENSE). Educational project.
