import { PriceResponse } from "../api";

const fmt = (x: number | null | undefined, d = 4) =>
  x === null || x === undefined ? "—" : x.toFixed(d);

export function ResultCard({ res }: { res: PriceResponse | null }) {
  if (!res) {
    return (
      <div className="panel">
        <h2>Result</h2>
        <p className="muted">Run a price to see results.</p>
      </div>
    );
  }
  const g = res.greeks;
  return (
    <div className="panel">
      <h2>Result — {res.method}</h2>
      <div className="result-row">
        <span className="label">Price</span>
        <span className="value big">{fmt(res.price, 4)}</span>
      </div>
      {res.std_error != null && (
        <div className="result-row">
          <span className="label">MC std err</span>
          <span className="value">±{fmt(res.std_error, 5)}</span>
        </div>
      )}
      {res.n_paths != null && (
        <div className="result-row">
          <span className="label">Paths</span>
          <span className="value">{res.n_paths.toLocaleString()}</span>
        </div>
      )}
      {res.n_steps != null && (
        <div className="result-row">
          <span className="label">Steps</span>
          <span className="value">{res.n_steps.toLocaleString()}</span>
        </div>
      )}
      <div className="result-row">
        <span className="label">Elapsed</span>
        <span className="value">{fmt(res.elapsed_ms, 1)} ms</span>
      </div>

      {g && (
        <table className="greeks-table">
          <thead>
            <tr>
              <th>Delta</th>
              <th>Gamma</th>
              <th>Vega</th>
              <th>Theta</th>
              <th>Rho</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{fmt(g.delta)}</td>
              <td>{fmt(g.gamma, 5)}</td>
              <td>{fmt(g.vega, 3)}</td>
              <td>{fmt(g.theta, 3)}</td>
              <td>{fmt(g.rho, 3)}</td>
            </tr>
          </tbody>
        </table>
      )}
    </div>
  );
}
