// C++ pricing engine with pybind11 bindings.
//
// Mirrors src/options_pricing/{black_scholes,binomial,monte_carlo}.py so we
// can benchmark a native implementation against the vectorized NumPy one.
//
// Build via setup.py (pybind11.setup_helpers); produced module is
// options_pricing._cpp_engine, re-exported as options_pricing.cpp_engine.

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include <algorithm>
#include <cmath>
#include <random>
#include <stdexcept>
#include <string>
#include <vector>

namespace py = pybind11;

namespace {

constexpr double SQRT_2 = 1.41421356237309504880;
constexpr double INV_SQRT_2PI = 0.39894228040143267794;
constexpr double EPS = 1e-12;

inline double norm_cdf(double x) {
    return 0.5 * std::erfc(-x / SQRT_2);
}
inline double norm_pdf(double x) {
    return INV_SQRT_2PI * std::exp(-0.5 * x * x);
}

bool is_call(const std::string& option_type) {
    if (option_type == "call") return true;
    if (option_type == "put")  return false;
    throw std::invalid_argument("option_type must be 'call' or 'put'");
}

// ---------------------------------------------------------------------------
// Black-Scholes-Merton
// ---------------------------------------------------------------------------

double bs_price(double S, double K, double T, double r, double sigma,
                double q, const std::string& option_type) {
    bool call = is_call(option_type);
    if (T <= EPS) {
        return call ? std::max(S - K, 0.0) : std::max(K - S, 0.0);
    }
    double sqrtT = std::sqrt(T);
    double d1 = (std::log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT);
    double d2 = d1 - sigma * sqrtT;
    double disc_r = std::exp(-r * T);
    double disc_q = std::exp(-q * T);
    if (call) {
        return S * disc_q * norm_cdf(d1) - K * disc_r * norm_cdf(d2);
    }
    return K * disc_r * norm_cdf(-d2) - S * disc_q * norm_cdf(-d1);
}

py::dict bs_greeks(double S, double K, double T, double r, double sigma,
                   double q, const std::string& option_type) {
    bool call = is_call(option_type);
    py::dict out;
    if (T <= EPS) {
        out["delta"] = 0.0; out["gamma"] = 0.0; out["vega"] = 0.0;
        out["theta"] = 0.0; out["rho"]   = 0.0;
        return out;
    }
    double sqrtT = std::sqrt(T);
    double d1 = (std::log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT);
    double d2 = d1 - sigma * sqrtT;
    double disc_r = std::exp(-r * T);
    double disc_q = std::exp(-q * T);
    double pdf_d1 = norm_pdf(d1);

    double gamma = disc_q * pdf_d1 / (S * sigma * sqrtT);
    double vega  = S * disc_q * pdf_d1 * sqrtT;
    double delta, theta, rho;

    if (call) {
        delta = disc_q * norm_cdf(d1);
        theta = -S * disc_q * pdf_d1 * sigma / (2 * sqrtT)
                - r * K * disc_r * norm_cdf(d2)
                + q * S * disc_q * norm_cdf(d1);
        rho   = K * T * disc_r * norm_cdf(d2);
    } else {
        delta = -disc_q * norm_cdf(-d1);
        theta = -S * disc_q * pdf_d1 * sigma / (2 * sqrtT)
                + r * K * disc_r * norm_cdf(-d2)
                - q * S * disc_q * norm_cdf(-d1);
        rho   = -K * T * disc_r * norm_cdf(-d2);
    }

    out["delta"] = delta;
    out["gamma"] = gamma;
    out["vega"]  = vega;
    out["theta"] = theta;
    out["rho"]   = rho;
    return out;
}

// ---------------------------------------------------------------------------
// Cox-Ross-Rubinstein binomial tree
// ---------------------------------------------------------------------------

double crr_price(double S, double K, double T, double r, double sigma,
                 double q, const std::string& option_type, int n_steps,
                 bool american) {
    bool call = is_call(option_type);
    if (n_steps < 1) throw std::invalid_argument("n_steps must be >= 1");
    if (T <= 0) return call ? std::max(S - K, 0.0) : std::max(K - S, 0.0);

    double dt = T / n_steps;
    double u  = std::exp(sigma * std::sqrt(dt));
    double d  = 1.0 / u;
    double p  = (std::exp((r - q) * dt) - d) / (u - d);
    double disc = std::exp(-r * dt);

    if (p < 0.0 || p > 1.0) {
        throw std::runtime_error("CRR risk-neutral probability out of [0,1]");
    }

    std::vector<double> values(n_steps + 1);
    // Terminal asset prices and payoffs
    for (int j = 0; j <= n_steps; ++j) {
        double ST = S * std::pow(u, n_steps - j) * std::pow(d, j);
        values[j] = call ? std::max(ST - K, 0.0) : std::max(K - ST, 0.0);
    }

    for (int step = n_steps - 1; step >= 0; --step) {
        for (int j = 0; j <= step; ++j) {
            values[j] = disc * (p * values[j] + (1 - p) * values[j + 1]);
            if (american) {
                double S_node = S * std::pow(u, step - j) * std::pow(d, j);
                double intrinsic = call ? std::max(S_node - K, 0.0)
                                        : std::max(K - S_node, 0.0);
                values[j] = std::max(values[j], intrinsic);
            }
        }
    }
    return values[0];
}

// ---------------------------------------------------------------------------
// Monte Carlo (European, antithetic + optional control variate)
// ---------------------------------------------------------------------------

py::dict mc_price(double S, double K, double T, double r, double sigma,
                  double q, const std::string& option_type,
                  long n_paths, bool antithetic, bool control_variate,
                  long seed) {
    bool call = is_call(option_type);
    if (n_paths < 2) throw std::invalid_argument("n_paths must be >= 2");
    if (antithetic && n_paths < 4)
        throw std::invalid_argument("n_paths must be >= 4 when antithetic (need >= 2 pairs)");

    py::dict out;
    if (T <= 0) {
        double intrinsic = call ? std::max(S - K, 0.0) : std::max(K - S, 0.0);
        out["price"] = intrinsic;
        out["std_error"] = 0.0;
        out["n_paths"] = n_paths;
        return out;
    }

    std::mt19937_64 rng(static_cast<uint64_t>(seed));
    std::normal_distribution<double> N01(0.0, 1.0);

    double drift = (r - q - 0.5 * sigma * sigma) * T;
    double vol   = sigma * std::sqrt(T);
    double disc  = std::exp(-r * T);
    double mu_X  = S * std::exp(-q * T);

    // Build per-sample (Y, X) observations. With antithetic each sample is
    // the (Z, -Z) pair average, so the SE captures the variance reduction.
    long n_eff = antithetic ? n_paths / 2 : n_paths;
    double sum_Y = 0.0, sum_Y2 = 0.0;
    double sum_X = 0.0, sum_X2 = 0.0, sum_XY = 0.0;

    for (long i = 0; i < n_eff; ++i) {
        double z = N01(rng);
        double Y, X;
        if (antithetic) {
            double ST_pos = S * std::exp(drift + vol * z);
            double ST_neg = S * std::exp(drift - vol * z);
            double p_pos = call ? std::max(ST_pos - K, 0.0) : std::max(K - ST_pos, 0.0);
            double p_neg = call ? std::max(ST_neg - K, 0.0) : std::max(K - ST_neg, 0.0);
            Y = 0.5 * disc * (p_pos + p_neg);
            X = 0.5 * disc * (ST_pos + ST_neg);
        } else {
            double ST = S * std::exp(drift + vol * z);
            double pay = call ? std::max(ST - K, 0.0) : std::max(K - ST, 0.0);
            Y = disc * pay;
            X = disc * ST;
        }
        sum_Y += Y;  sum_Y2 += Y * Y;
        sum_X += X;  sum_X2 += X * X;  sum_XY += X * Y;
    }
    double inv_n = 1.0 / static_cast<double>(n_eff);
    double mean_Y = sum_Y * inv_n;
    double var_Y  = (sum_Y2 - n_eff * mean_Y * mean_Y) / (n_eff - 1);
    double price = mean_Y;
    double final_var = var_Y;

    if (control_variate) {
        double mean_X = sum_X * inv_n;
        double var_X  = (sum_X2 - n_eff * mean_X * mean_X) / (n_eff - 1);
        double cov_XY = (sum_XY - n_eff * mean_X * mean_Y) / (n_eff - 1);
        if (var_X > 0) {
            double beta = cov_XY / var_X;
            price = mean_Y - beta * (mean_X - mu_X);
            final_var = var_Y - beta * beta * var_X;
            if (final_var < 0) final_var = 0;
        }
    }

    double std_err = std::sqrt(final_var / n_eff);

    out["price"]     = price;
    out["std_error"] = std_err;
    // Report the requested total path count, matching the Python engine's
    // PricingResult.n_paths convention (pairs are an internal detail).
    out["n_paths"]   = n_paths;
    out["antithetic"]      = antithetic;
    out["control_variate"] = control_variate;
    return out;
}

}  // namespace

PYBIND11_MODULE(_cpp_engine, m) {
    m.doc() = "Native C++ pricing engine (BSM, CRR, MC). Matches the Python "
              "reference implementation in src/options_pricing/.";

    m.def("bs_price", &bs_price,
          py::arg("S"), py::arg("K"), py::arg("T"), py::arg("r"),
          py::arg("sigma"), py::arg("q") = 0.0,
          py::arg("option_type") = std::string("call"),
          "Black-Scholes-Merton European price.");

    m.def("bs_greeks", &bs_greeks,
          py::arg("S"), py::arg("K"), py::arg("T"), py::arg("r"),
          py::arg("sigma"), py::arg("q") = 0.0,
          py::arg("option_type") = std::string("call"),
          "Analytical BSM Greeks as dict(delta, gamma, vega, theta, rho).");

    m.def("crr_price", &crr_price,
          py::arg("S"), py::arg("K"), py::arg("T"), py::arg("r"),
          py::arg("sigma"), py::arg("q") = 0.0,
          py::arg("option_type") = std::string("call"),
          py::arg("n_steps") = 500,
          py::arg("american") = false,
          "Cox-Ross-Rubinstein binomial price (European or American).");

    m.def("mc_price", &mc_price,
          py::arg("S"), py::arg("K"), py::arg("T"), py::arg("r"),
          py::arg("sigma"), py::arg("q") = 0.0,
          py::arg("option_type") = std::string("call"),
          py::arg("n_paths") = 100000L,
          py::arg("antithetic") = true,
          py::arg("control_variate") = true,
          py::arg("seed") = 42L,
          "European Monte Carlo price. Returns dict(price, std_error, n_paths, ...).");
}
