import { useEffect, useState } from "react";

import { api, OptionInputs, Method, PriceResponse } from "../api";
import { useDebounced } from "../hooks/useDebounced";

interface Props {
  inputs: OptionInputs;
}

interface Row {
  method: Method;
  res: PriceResponse | null;
  err?: string;
}

export function MethodComparison({ inputs: rawInputs }: Props) {
  // Debounced: three pricing calls (incl. a 200k-path MC) per refresh.
  const inputs = useDebounced(rawInputs, 400);
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const methods: Method[] = ["black_scholes", "binomial", "monte_carlo"];
    Promise.all(
      methods.map(m =>
        api.price({
          ...inputs, method: m,
          n_steps: 500, n_paths: 200_000, seed: 42,
        }).then(
          res => ({ method: m, res } as Row),
          e => ({ method: m, res: null, err: String(e) } as Row),
        ),
      ),
    ).then(r => {
      if (!cancelled) setRows(r);
    }).finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [inputs.S, inputs.K, inputs.T, inputs.r, inputs.sigma, inputs.q, inputs.option_type]);

  const bsmRef = rows.find(r => r.method === "black_scholes")?.res?.price;

  return (
    <div className="panel">
      <h2>Method Comparison</h2>
      <p className="muted" style={{ fontSize: 12, margin: "0 0 12px" }}>
        All three methods, same inputs. Binomial uses 500 steps; MC uses 200k paths with antithetic + control variate.
      </p>
      <table className="compare-table">
        <thead>
          <tr>
            <th>Method</th>
            <th>Price</th>
            <th>Δ vs BSM</th>
            <th>Std err</th>
            <th>Time (ms)</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(r => {
            const p = r.res?.price;
            const diff = (p != null && bsmRef != null) ? p - bsmRef : null;
            return (
              <tr key={r.method}>
                <td>{r.method}</td>
                <td>{p != null ? p.toFixed(4) : "—"}</td>
                <td>{diff != null ? (diff >= 0 ? "+" : "") + diff.toFixed(4) : "—"}</td>
                <td>{r.res?.std_error != null ? "±" + r.res.std_error.toFixed(5) : "—"}</td>
                <td>{r.res?.elapsed_ms?.toFixed(1) ?? "—"}</td>
              </tr>
            );
          })}
          {loading && <tr><td colSpan={5} className="muted">Loading…</td></tr>}
        </tbody>
      </table>
    </div>
  );
}
