import { OptionInputs, OptionType, Method } from "../api";

interface Props {
  inputs: OptionInputs;
  setInputs: (i: OptionInputs) => void;
  method: Method;
  setMethod: (m: Method) => void;
  american: boolean;
  setAmerican: (a: boolean) => void;
  nSteps: number;
  setNSteps: (n: number) => void;
  nPaths: number;
  setNPaths: (n: number) => void;
  onPrice: () => void;
  loading: boolean;
}

const num = (v: string, fallback: number) => {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : fallback;
};

export function PricerForm(p: Props) {
  const set = (patch: Partial<OptionInputs>) => p.setInputs({ ...p.inputs, ...patch });

  return (
    <div className="panel">
      <h2>Option Inputs</h2>

      <div className="method-pills">
        {(["black_scholes", "binomial", "monte_carlo"] as Method[]).map(m => (
          <button
            key={m}
            className={p.method === m ? "active" : ""}
            onClick={() => p.setMethod(m)}
          >
            {m === "black_scholes" ? "BSM" : m === "binomial" ? "Binomial" : "Monte Carlo"}
          </button>
        ))}
      </div>

      <div className="form-row">
        <label>Spot S</label>
        <input type="number" step="0.01" value={p.inputs.S}
               onChange={e => set({ S: num(e.target.value, p.inputs.S) })} />
      </div>
      <div className="form-row">
        <label>Strike K</label>
        <input type="number" step="0.01" value={p.inputs.K}
               onChange={e => set({ K: num(e.target.value, p.inputs.K) })} />
      </div>
      <div className="form-row">
        <label>T (years)</label>
        <input type="number" step="0.01" value={p.inputs.T}
               onChange={e => set({ T: num(e.target.value, p.inputs.T) })} />
      </div>
      <div className="form-row">
        <label>Rate r</label>
        <input type="number" step="0.001" value={p.inputs.r}
               onChange={e => set({ r: num(e.target.value, p.inputs.r) })} />
      </div>
      <div className="form-row">
        <label>Sigma σ</label>
        <input type="number" step="0.01" value={p.inputs.sigma}
               onChange={e => set({ sigma: num(e.target.value, p.inputs.sigma) })} />
      </div>
      <div className="form-row">
        <label>Div. yield q</label>
        <input type="number" step="0.001" value={p.inputs.q}
               onChange={e => set({ q: num(e.target.value, p.inputs.q) })} />
      </div>
      <div className="form-row">
        <label>Type</label>
        <select value={p.inputs.option_type}
                onChange={e => set({ option_type: e.target.value as OptionType })}>
          <option value="call">Call</option>
          <option value="put">Put</option>
        </select>
      </div>

      {p.method === "binomial" && (
        <>
          <div className="form-row">
            <label>Tree steps</label>
            <input type="number" min="10" step="10" value={p.nSteps}
                   onChange={e => p.setNSteps(num(e.target.value, p.nSteps))} />
          </div>
          <label className="checkbox-row">
            <input type="checkbox" checked={p.american}
                   onChange={e => p.setAmerican(e.target.checked)} />
            American exercise
          </label>
        </>
      )}

      {p.method === "monte_carlo" && (
        <div className="form-row">
          <label>Paths</label>
          <input type="number" min="100" step="1000" value={p.nPaths}
                 onChange={e => p.setNPaths(num(e.target.value, p.nPaths))} />
        </div>
      )}

      <button className="btn" onClick={p.onPrice} disabled={p.loading}>
        {p.loading ? "Pricing…" : "Price"}
      </button>
    </div>
  );
}
