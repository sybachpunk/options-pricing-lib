# Frontend — notes

React + TypeScript + Vite SPA. Charts are [Recharts](https://recharts.org/). The
whole UI is a thin client over the FastAPI backend — no pricing math runs in the
browser.

Run it: `npm install && npm run dev` → `http://localhost:5173`
(The backend must be running on `:8000`; Vite proxies `/api/*` to it — see
`vite.config.ts`.)

## Component map

| File | Role |
|------|------|
| `src/App.tsx` | top-level state (inputs, method, result) + tab layout |
| `src/api.ts` | typed `fetch` wrapper; mirrors the backend Pydantic schemas |
| `src/hooks/useDebounced.ts` | trailing-debounce hook used by the chart panels |
| `components/PricerForm.tsx` | option inputs, method pills, method-specific fields (tree steps / MC paths / American toggle) |
| `components/ResultCard.tsx` | price, MC std-error, timing, and the Greeks row |
| `components/ConvergencePlot.tsx` | MC price ±2σ band vs. path count, with the BSM reference line |
| `components/PayoffDiagram.tsx` | intrinsic value and P&L-net-of-premium at expiry |
| `components/MethodComparison.tsx` | all three methods side-by-side, same inputs |

## Things worth knowing

- **The convergence/compare panels refetch when inputs change**, debounced by 400ms
  (`useDebounced`) so a pause in typing triggers one request rather than one per
  keystroke — the convergence sweep runs ~1M+ simulated paths server-side per refresh.
- **The std-error band in `ConvergencePlot`** is drawn with a stacked-`Area` trick
  (upper band filled, lower band filled with the background color) because Recharts
  has no first-class "band" series. It's a visual hack, not data — the real numbers
  are the line and the BSM reference.
- **Types are kept in lockstep with `backend/schemas.py` by hand.** If you change a
  schema, update `api.ts`. There's no codegen.
- **`option_type`/`method` are string unions**, matching the backend exactly.
