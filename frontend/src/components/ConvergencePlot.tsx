import { useEffect, useState } from "react";
import {
  ResponsiveContainer, Line, XAxis, YAxis, Tooltip, ReferenceLine,
  CartesianGrid, Legend, Area, ComposedChart,
} from "recharts";

import { api, OptionInputs } from "../api";
import { useDebounced } from "../hooks/useDebounced";

interface Props {
  inputs: OptionInputs;
}

export function ConvergencePlot({ inputs: rawInputs }: Props) {
  // Debounce so the convergence sweep (a large simulation server-side)
  // runs once per pause in typing, not once per keystroke.
  const inputs = useDebounced(rawInputs, 400);
  const [data, setData] = useState<any[]>([]);
  const [ref, setRef] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    api.convergence({
      ...inputs,
      path_counts: [1000, 2000, 5000, 10000, 25000, 50000, 100000, 250000, 500000],
      seed: 42,
    })
      .then(r => {
        if (cancelled) return;
        setRef(r.bsm_reference);
        setData(r.points.map(p => ({
          n: p.n_paths,
          price: p.price,
          se_upper: p.price + 2 * p.std_error,
          se_lower: p.price - 2 * p.std_error,
        })));
      })
      .catch(e => !cancelled && setErr(String(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [inputs.S, inputs.K, inputs.T, inputs.r, inputs.sigma, inputs.q, inputs.option_type]);

  return (
    <div className="panel">
      <h2>Monte Carlo Convergence</h2>
      <p className="muted" style={{ fontSize: 12, margin: "0 0 12px" }}>
        Price (with ±2σ band) versus number of paths. Dashed line is the closed-form BSM price.
        Error shrinks as O(1/√N) — doubling accuracy requires 4× the paths.
      </p>
      {err && <p className="error">{err}</p>}
      {loading && <p className="muted">Loading…</p>}
      <div className="chart-wrap">
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#2d3548" strokeDasharray="3 3" />
            <XAxis
              dataKey="n"
              scale="log"
              domain={["auto", "auto"]}
              type="number"
              stroke="#8b94a8"
              tickFormatter={(v: number) => v >= 1000 ? `${v / 1000}k` : `${v}`}
            />
            <YAxis stroke="#8b94a8" domain={["auto", "auto"]} />
            <Tooltip
              contentStyle={{ background: "#1a1f2e", border: "1px solid #2d3548" }}
              formatter={(v: any) => typeof v === "number" ? v.toFixed(4) : v}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area dataKey="se_upper" stroke="none" fill="#4a9eff" fillOpacity={0.15} legendType="none" />
            <Area dataKey="se_lower" stroke="none" fill="#0f1419" fillOpacity={1} legendType="none" />
            <Line type="monotone" dataKey="price" stroke="#4a9eff" strokeWidth={2} dot={{ r: 3 }} name="MC price" />
            {ref != null && (
              <ReferenceLine y={ref} stroke="#f5a623" strokeDasharray="5 5" label={{ value: "BSM", fill: "#f5a623", fontSize: 11 }} />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
