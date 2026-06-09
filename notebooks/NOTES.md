# Notebook — notes

`pricing_showcase.ipynb` is the **main portfolio deliverable**. It's meant to be read
top-to-bottom as a narrated tour of the library, not just executed.

Launch: `jupyter notebook notebooks/pricing_showcase.ipynb` (after `pip install -e ".[dev]"`).

## Section map

1. **Setup** — imports; prints whether the C++ engine is loaded.
2. **Black-Scholes-Merton** — closed form + a put-call parity check.
3. **Greeks** — analytical vs. finite-difference table; delta/gamma-vs-spot plots.
4. **Binomial tree** — CRR → BSM convergence (with the even-odd oscillation visible);
   American-put early-exercise premium.
5. **Monte Carlo** — variance-reduction comparison and the log-log std-error plot whose
   **slope of −½ is the visual proof of `O(1/√N)`**.
6. **Accuracy comparison table** — all three methods across five scenarios, with timings.
7. **Exotics** — Asian (cheaper than vanilla) and barrier in/out parity.
8. **Implied-vol smile** — Brent solver round-trip on a synthetic skewed surface.
9. **C++ vs Python benchmark** — auto-skips with a message if the engine isn't built.
10. **When to use which method** — the written trade-off analysis across the three methods.

## Running notes

- The notebook puts `../src` on the path itself, so it runs from the repo without an
  install — though installing is cleaner.
- Cells are ordered; **run top-to-bottom**. Later cells reuse variables (`bsm`, `args`).
- The C++ benchmark cell is the only one that needs the native engine; everything else
  runs on pure Python.
- Outputs aren't committed — run the cells to regenerate plots and the benchmark.
- The benchmark numbers are machine-dependent; expect roughly **BSM ~100–180×**,
  **CRR ~15×**, **MC ~2×** speedups (MC is close because NumPy already vectorizes it
  in C — see the README discussion).
