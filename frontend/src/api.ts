// Thin wrapper around the FastAPI backend. All endpoints are POST with JSON body.

export type OptionType = "call" | "put";
export type Method = "black_scholes" | "binomial" | "monte_carlo";

export interface OptionInputs {
  S: number;
  K: number;
  T: number;
  r: number;
  sigma: number;
  q: number;
  option_type: OptionType;
}

export interface PriceRequest extends OptionInputs {
  method: Method;
  american?: boolean;
  n_steps?: number;
  n_paths?: number;
  antithetic?: boolean;
  control_variate?: boolean;
  seed?: number;
}

export interface Greeks {
  delta: number;
  gamma: number;
  vega: number;
  theta: number;
  rho: number;
}

export interface PriceResponse {
  price: number;
  method: string;
  std_error?: number | null;
  n_paths?: number | null;
  n_steps?: number | null;
  elapsed_ms: number;
  greeks?: Greeks | null;
}

export interface ConvergencePoint {
  n_paths: number;
  price: number;
  std_error: number;
}

export interface ConvergenceResponse {
  bsm_reference: number;
  points: ConvergencePoint[];
}

async function post<TReq, TRes>(path: string, body: TReq): Promise<TRes> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  price: (req: PriceRequest) => post<PriceRequest, PriceResponse>("/api/price", req),

  convergence: (req: OptionInputs & { path_counts?: number[]; seed?: number }) =>
    post<typeof req, ConvergenceResponse>("/api/convergence", req),

  impliedVol: (req: {
    market_price: number;
    S: number; K: number; T: number; r: number; q: number;
    option_type: OptionType;
  }) => post<typeof req, { implied_vol: number; elapsed_ms: number }>("/api/implied_vol", req),

  asian: (req: OptionInputs & { n_paths?: number; n_steps?: number; seed?: number }) =>
    post<typeof req, PriceResponse>("/api/asian", req),

  barrier: (req: OptionInputs & {
    barrier: number;
    kind: "up-and-out" | "down-and-out" | "up-and-in" | "down-and-in";
    n_paths?: number; n_steps?: number; seed?: number;
  }) => post<typeof req, PriceResponse>("/api/barrier", req),

  health: () => fetch("/api/health").then(r => r.json()),
};
