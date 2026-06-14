"""
Experimentation layer — does the recommender *cause* a lift, or do these products
just co-occur?

The affinity engine proves ASSOCIATION (lift > 1). It cannot prove that *showing*
a recommendation causes incremental purchases — customers who buy more buy more of
everything (selection bias). Establishing causation requires a randomized experiment.

This module does the part you'd actually own as an analyst:
  1. Pulls real baselines from the warehouse (AOV moments, natural attach rate, return rate).
  2. Sizes the experiment (power analysis) for two candidate primary metrics.
  3. Shows how CUPED variance reduction shrinks the required sample.
  4. Monte-Carlo simulates the experiment to confirm the design hits its target power
     and controls the false-positive rate under the null.
  5. Applies the pre-registered decision rule.

NOTE: outcomes are SIMULATED — there is no live recommender to A/B test on a 2011
dataset. The deliverable is the *design and analysis methodology*, which is what the
decision actually hinges on. Baselines, however, are real (read from DuckDB).
"""
from __future__ import annotations

import pathlib

import duckdb
import numpy as np
from scipy import stats
from statsmodels.stats.power import NormalIndPower, TTestIndPower
from statsmodels.stats.proportion import proportion_effectsize, proportions_ztest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "retail.duckdb"

ALPHA = 0.05            # one-sided: we only ship a positive lift
POWER = 0.80
RNG = np.random.default_rng(42)


# --------------------------------------------------------------------------- #
# 1. Real baselines from the warehouse
# --------------------------------------------------------------------------- #
def load_baselines() -> dict:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    mean_aov, sd_aov = con.execute(
        """
        WITH ov AS (SELECT invoice_no, sum(line_revenue) aov
                    FROM analytics.int_order_lines GROUP BY 1)
        SELECT avg(aov), stddev(aov) FROM ov
        """
    ).fetchone()
    attach = con.execute(
        "SELECT median(confidence) FROM analytics.mart_product_affinity"
    ).fetchone()[0]
    return_rate = con.execute(
        """
        SELECT count(DISTINCT invoice_no) FILTER (WHERE is_cancellation)::DOUBLE
             / count(DISTINCT invoice_no)
        FROM analytics.stg_transactions
        """
    ).fetchone()[0]
    con.close()
    return {
        "mean_aov": mean_aov,
        "sd_aov": sd_aov,
        "attach_rate": attach,
        "return_rate": return_rate,
    }


# --------------------------------------------------------------------------- #
# 2-3. Power analysis / sample sizing
# --------------------------------------------------------------------------- #
def size_binary(p0: float, rel_mde: float) -> tuple[float, int]:
    """Sample size per arm for a proportion (attach rate)."""
    p1 = p0 * (1 + rel_mde)
    es = proportion_effectsize(p1, p0)
    n = NormalIndPower().solve_power(es, alpha=ALPHA, power=POWER, alternative="larger")
    return p1, int(np.ceil(n))


def size_continuous(mean: float, sd: float, rel_mde: float, cuped_rho: float = 0.0) -> int:
    """Sample size per arm for a mean (AOV). cuped_rho>0 models variance reduction."""
    sd_eff = sd * np.sqrt(1 - cuped_rho**2)      # CUPED cuts variance by (1 - rho^2)
    d = (mean * rel_mde) / sd_eff                # Cohen's d for the MDE
    n = TTestIndPower().solve_power(d, alpha=ALPHA, power=POWER, alternative="larger")
    return int(np.ceil(n))


# --------------------------------------------------------------------------- #
# 4. Monte-Carlo validation
# --------------------------------------------------------------------------- #
def simulate_binary(n: int, p_ctrl: float, p_treat: float, sims: int = 2000) -> float:
    """Return empirical power (or false-positive rate if p_treat == p_ctrl)."""
    hits = 0
    for _ in range(sims):
        c = RNG.binomial(n, p_ctrl)
        t = RNG.binomial(n, p_treat)
        _, p = proportions_ztest([t, c], [n, n], alternative="larger")
        hits += p < ALPHA
    return hits / sims


def simulate_aov(n: int, mean: float, sd: float, rel_effect: float, sims: int = 1000) -> float:
    """Lognormal-matched AOV; Welch t-test on log scale (handles the skew)."""
    sigma = np.sqrt(np.log(1 + (sd / mean) ** 2))
    mu = np.log(mean) - sigma**2 / 2
    hits = 0
    for _ in range(sims):
        ctrl = RNG.lognormal(mu, sigma, n)
        treat = RNG.lognormal(mu, sigma, n) * (1 + rel_effect)
        _, p = stats.ttest_ind(np.log(treat), np.log(ctrl), equal_var=False)
        # one-sided
        hits += (p / 2 < ALPHA) and (treat.mean() > ctrl.mean())
    return hits / sims


# --------------------------------------------------------------------------- #
# 5. Decision rule
# --------------------------------------------------------------------------- #
def decision(primary_sig: bool, primary_positive: bool, guardrail_ok: bool) -> str:
    if primary_sig and primary_positive and guardrail_ok:
        return "SHIP — primary metric lifted, guardrail held."
    if primary_sig and primary_positive and not guardrail_ok:
        return "HOLD — lift real but guardrail (returns) breached; investigate before ship."
    return "DO NOT SHIP — no significant positive effect on the primary metric."


def main() -> None:
    b = load_baselines()
    print("=" * 68)
    print("EXPERIMENT: 'Frequently bought together' recommender")
    print("=" * 68)
    print("\nReal baselines (from warehouse):")
    print(f"  mean AOV         : £{b['mean_aov']:.2f}")
    print(f"  sd AOV           : £{b['sd_aov']:.2f}  (CV={b['sd_aov']/b['mean_aov']:.1f} — heavy skew)")
    print(f"  natural attach   : {b['attach_rate']*100:.1f}%  (median pair confidence)")
    print(f"  return rate      : {b['return_rate']*100:.1f}%  (guardrail)")

    print("\n--- Sample sizing (alpha={:.2f}, power={:.0%}, one-sided) ---".format(ALPHA, POWER))

    # Primary: attach rate, +20% relative lift
    p1, n_bin = size_binary(b["attach_rate"], rel_mde=0.20)
    print(f"\nPRIMARY = attach rate  ({b['attach_rate']*100:.1f}% -> {p1*100:.1f}%, +20% rel)")
    print(f"  required n/arm   : {n_bin:,}")

    # Secondary: AOV, +3% relative — raw vs CUPED
    n_aov = size_continuous(b["mean_aov"], b["sd_aov"], rel_mde=0.03)
    n_cuped = size_continuous(b["mean_aov"], b["sd_aov"], rel_mde=0.03, cuped_rho=0.5)
    print(f"\nSECONDARY = AOV  (+3% rel)")
    print(f"  required n/arm   : {n_aov:,}  (raw)")
    print(f"  required n/arm   : {n_cuped:,}  (with CUPED, rho=0.5 -> {1-n_cuped/n_aov:.0%} fewer)")
    print("  -> AOV is too noisy to be the primary; use attach rate, AOV as north-star.")

    print("\n--- Monte-Carlo validation (attach rate is primary) ---")
    emp_power = simulate_binary(n_bin, b["attach_rate"], p1)
    fpr = simulate_binary(n_bin, b["attach_rate"], b["attach_rate"])
    print(f"  empirical power  : {emp_power:.1%}  (target {POWER:.0%})")
    print(f"  false-pos (null) : {fpr:.1%}  (target <= {ALPHA:.0%})")

    print("\n--- A single simulated readout (true +20% attach lift) ---")
    c = RNG.binomial(n_bin, b["attach_rate"])
    t = RNG.binomial(n_bin, p1)
    stat, pval = proportions_ztest([t, c], [n_bin, n_bin], alternative="larger")
    lift = (t / n_bin) / (c / n_bin) - 1
    # guardrail: simulate return rate unchanged
    rc = RNG.binomial(n_bin, b["return_rate"]); rt = RNG.binomial(n_bin, b["return_rate"])
    _, p_guard = proportions_ztest([rt, rc], [n_bin, n_bin], alternative="larger")
    guard_ok = p_guard > ALPHA
    print(f"  observed lift    : {lift:+.1%}   (p={pval:.4f})")
    print(f"  guardrail returns: p={p_guard:.3f} -> {'held' if guard_ok else 'BREACHED'}")
    print(f"\n  DECISION: {decision(pval < ALPHA, lift > 0, guard_ok)}")
    print("=" * 68)


if __name__ == "__main__":
    main()
