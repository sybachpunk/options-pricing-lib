import { useMemo } from "react";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip,
  CartesianGrid, ReferenceLine, Legend,
} from "recharts";

import { OptionInputs, PriceResponse } from "../api";

interface Props {
  inputs: OptionInputs;
  result: PriceResponse | null;
}

export function PayoffDiagram({ inputs, result }: Props) {
  const data = useMemo(() => {
    const { K, option_type } = inputs;
    const premium = result?.price ?? 0;
    const center = inputs.S;
    const half = Math.max(center * 0.6, K * 0.6);
    const lo = Math.max(1, center - half);
    const hi = center + half;
    const N = 80;
    const rows = [];
    for (let i = 0; i <= N; i++) {
      const ST = lo + (hi - lo) * i / N;
      const intrinsic = option_type === "call"
        ? Math.max(ST - K, 0)
        : Math.max(K - ST, 0);
      const pnl = intrinsic - premium;
      rows.push({ ST, intrinsic, pnl });
    }
    return rows;
  }, [inputs, result]);

  return (
    <div className="panel">
      <h2>Payoff at Expiry</h2>
      <p className="muted" style={{ fontSize: 12, margin: "0 0 12px" }}>
        Intrinsic value (blue) and P&L net of premium (orange) as a function of underlying at expiry.
      </p>
      <div className="chart-wrap">
        <ResponsiveContainer>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid stroke="#2d3548" strokeDasharray="3 3" />
            <XAxis
              dataKey="ST"
              stroke="#8b94a8"
              type="number"
              domain={["auto", "auto"]}
              tickFormatter={(v: number) => v.toFixed(0)}
              label={{ value: "S at expiry", fill: "#8b94a8", position: "insideBottom", offset: -2, fontSize: 11 }}
            />
            <YAxis stroke="#8b94a8" />
            <Tooltip
              contentStyle={{ background: "#1a1f2e", border: "1px solid #2d3548" }}
              formatter={(v: any) => typeof v === "number" ? v.toFixed(3) : v}
              labelFormatter={(v: any) => `S_T = ${typeof v === "number" ? v.toFixed(2) : v}`}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <ReferenceLine x={inputs.K} stroke="#8b94a8" strokeDasharray="2 4" label={{ value: "K", fill: "#8b94a8", fontSize: 11 }} />
            <ReferenceLine y={0} stroke="#2d3548" />
            <Line type="monotone" dataKey="intrinsic" stroke="#4a9eff" strokeWidth={2} dot={false} name="Intrinsic" />
            <Line type="monotone" dataKey="pnl" stroke="#f5a623" strokeWidth={2} dot={false} name="P&L (net of premium)" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
