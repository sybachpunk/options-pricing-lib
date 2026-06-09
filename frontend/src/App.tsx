import { useState } from "react";

import { api, OptionInputs, Method, PriceResponse } from "./api";
import { PricerForm } from "./components/PricerForm";
import { ResultCard } from "./components/ResultCard";
import { ConvergencePlot } from "./components/ConvergencePlot";
import { PayoffDiagram } from "./components/PayoffDiagram";
import { MethodComparison } from "./components/MethodComparison";

const DEFAULT_INPUTS: OptionInputs = {
  S: 100,
  K: 100,
  T: 1.0,
  r: 0.05,
  sigma: 0.25,
  q: 0.0,
  option_type: "call",
};

type Tab = "convergence" | "payoff" | "compare";

export default function App() {
  const [inputs, setInputs] = useState<OptionInputs>(DEFAULT_INPUTS);
  const [method, setMethod] = useState<Method>("black_scholes");
  const [american, setAmerican] = useState(false);
  const [nSteps, setNSteps] = useState(500);
  const [nPaths, setNPaths] = useState(200_000);
  const [result, setResult] = useState<PriceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("convergence");

  const handlePrice = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await api.price({
        ...inputs,
        method,
        american,
        n_steps: nSteps,
        n_paths: nPaths,
        seed: 42,
      });
      setResult(r);
    } catch (e: any) {
      setError(e.message || String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1>Options Pricing Lab</h1>
          <span className="subtitle">
            Black-Scholes-Merton · CRR binomial · Monte Carlo
          </span>
        </div>
        <span className="muted">Python + C++ engine · FastAPI · React</span>
      </header>

      <div className="grid">
        <div>
          <PricerForm
            inputs={inputs}
            setInputs={setInputs}
            method={method}
            setMethod={setMethod}
            american={american}
            setAmerican={setAmerican}
            nSteps={nSteps}
            setNSteps={setNSteps}
            nPaths={nPaths}
            setNPaths={setNPaths}
            onPrice={handlePrice}
            loading={loading}
          />
          {error && <p className="error">{error}</p>}
          <div style={{ marginTop: 24 }}>
            <ResultCard res={result} />
          </div>
        </div>

        <div className="right-stack">
          <div className="panel" style={{ paddingBottom: 0 }}>
            <div className="tabs">
              <button className={tab === "convergence" ? "active" : ""}
                      onClick={() => setTab("convergence")}>Convergence</button>
              <button className={tab === "payoff" ? "active" : ""}
                      onClick={() => setTab("payoff")}>Payoff</button>
              <button className={tab === "compare" ? "active" : ""}
                      onClick={() => setTab("compare")}>Compare methods</button>
            </div>
          </div>
          {tab === "convergence" && <ConvergencePlot inputs={inputs} />}
          {tab === "payoff" && <PayoffDiagram inputs={inputs} result={result} />}
          {tab === "compare" && <MethodComparison inputs={inputs} />}
        </div>
      </div>
    </div>
  );
}
