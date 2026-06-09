# C++ engine — notes

A native port of the hot pricers (BSM, CRR, MC) exposed to Python via pybind11.
It exists for two reasons: a real speedup benchmark, and a second independent
implementation that cross-validates the Python reference.

## Files

- `bindings.cpp` — the entire engine in one translation unit. Functions mirror
  `src/options_pricing/{black_scholes,binomial,monte_carlo}.py`. The module is
  built as `options_pricing._cpp_engine` and re-exported as
  `options_pricing.cpp_engine` (which is `None` when the extension isn't built).
- `CMakeLists.txt` — standalone CMake build for IDE integration. **Not** the
  primary build path — `setup.py` is.

## The parity contract

`tests/test_cpp_engine.py` asserts the C++ output matches Python to ~1e-10 for
BSM and CRR, and within the reported standard error for MC. **If you change a
formula on one side, change it on the other**, or the parity tests fail (which is
the point — they catch divergence).

What's intentionally *not* ported: `crr_greeks`, implied vol, and the exotics.
They're either not hot or not worth the C++ surface area for a portfolio project.
Greeks for the C++ path go through Python `fd_greeks` if needed.

## Building

Opt-in, because not every machine has a C++17 toolchain:

```bash
# macOS / Linux
OPTIONS_PRICING_BUILD_CPP=1 pip install -e ".[dev]"
```
```powershell
# Windows (needs MSVC Build Tools)
$env:OPTIONS_PRICING_BUILD_CPP="1"; pip install -e ".[dev]"
```

Without the env var you get a pure-Python install and the 4 C++ tests skip.

## Implementation notes

- `norm_cdf` uses `std::erfc` — no external stats dependency.
- MC uses `std::mt19937_64`; the antithetic path averages each `(Z, −Z)` pair into
  a single observation so the reported standard error reflects the genuine variance
  reduction (matching the Python implementation — keep them in sync).
- The returned `n_paths` is the requested total path count, same convention as the
  Python engine's `PricingResult.n_paths`; pair bookkeeping is an internal detail.
- Compiled with `/O2` (MSVC) or `-O3 -ffast-math` (gcc/clang). `-ffast-math` is fine
  here because we have no NaN/Inf-dependent control flow in the hot loops.
