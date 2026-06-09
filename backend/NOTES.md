# Backend — notes

A thin FastAPI layer over `options_pricing`. No business logic lives here beyond
input validation and choosing which library function to call — the math stays in
the library so the notebook, tests, and API all exercise the same code.

Run it: `uvicorn backend.main:app --reload --port 8000`
Interactive docs: `http://localhost:8000/docs` (FastAPI's auto-generated Swagger UI).

## Endpoints

| Method + path | Purpose | Notes |
|---------------|---------|-------|
| `GET  /api/health` | liveness + whether the C++ engine is loaded | — |
| `POST /api/price` | price + Greeks via BSM, binomial, or MC | see "Greeks per method" below |
| `POST /api/convergence` | MC price + std-error at a sweep of path counts, plus the BSM reference | feeds the convergence chart |
| `POST /api/implied_vol` | invert BSM for σ from a market price | 400 if the price violates arbitrage bounds |
| `POST /api/asian` | arithmetic Asian via MC (geometric control variate) | path-dependent |
| `POST /api/barrier` | knock-in/out barrier via MC | 400 if barrier is on the wrong side of spot |

## Greeks per method (important)

- **`black_scholes`** → analytical closed-form Greeks (`bs_greeks`). Exact, instant.
- **`binomial`** → tree-based Greeks (`crr_greeks`): delta/gamma off the lattice,
  theta off the step-2 node (correctly negative), vega/rho by bumped-tree FD.
- **`monte_carlo`** → finite-difference Greeks over the MC pricer, **with the seed
  pinned** so every bump shares random numbers (common random numbers). Without that
  the Greeks would be pure noise.

American exercise is only valid for `method=binomial`; the API returns **400** if you
ask BSM or MC for an American price, rather than silently giving a European answer.

## Conventions

- Schemas live in `schemas.py` (Pydantic v2, `extra="forbid"` so typos 422 loudly).
- CORS allows any `localhost`/`127.0.0.1` port for the Vite dev server.
- All numeric inputs are validated for sign/range at the edge, so the library
  functions can assume clean inputs.
