# Experiment Design — Does the Recommender Cause a Lift?

> **The point of this document.** The affinity engine (`mart_product_affinity`) proves
> that products *co-occur* — lift > 1. It does **not** prove that *showing* a
> recommendation *causes* incremental purchases. The two are different claims, and
> conflating them is the most common analytics mistake. This is the design and analysis
> for the randomized experiment that would settle it.
>
> **Honesty note:** there is no live storefront to test on a 2011 dataset, so the
> *outcomes* in `src/experiment.py` are simulated. The **baselines are real** (read from
> the warehouse) and the **methodology is what's being demonstrated** — sizing, metric
> choice, analysis, and the decision rule. That methodology is identical whether the data
> is simulated or live.

## Why observational data can't answer this

In the historical data, baskets containing both items of a high-lift pair are larger than
baskets containing only one. That's **not** evidence the recommendation works — it's
**selection bias**: customers who buy more buy more of *everything*. The co-purchase and
the larger basket share a common cause (an engaged buyer). Only randomization breaks that
confound.

## Hypothesis

> Showing a "frequently bought together" module (top complements from `mart_recommendations`)
> on the product/cart page increases the rate at which the recommended complement is added
> to the order, without increasing returns.

## Design

| Element | Choice | Why |
|---|---|---|
| Unit of randomization | Session (or user) | The recommendation is shown per session; randomize where the intervention lives. |
| Assignment | 50/50 control vs treatment | Equal arms maximize power for a fixed sample. |
| Control | No module (or a non-personalized "popular items") | Isolates the *personalized* reco effect. |

## Metrics

**Primary — complement attach rate (binary).** Did the order include the recommended
complement? Chosen as primary because it's *directly downstream of the mechanism* and far
less noisy than revenue. Real baseline: **8.1%** (median pair confidence).

**North-star — AOV (continuous).** The business metric, but heavy-tailed: mean £476,
SD £1,679 (**CV ≈ 3.5**). That noise makes it a poor *primary* — see sizing below — so it's
tracked as a secondary, ideally with **CUPED** variance reduction using pre-period spend.

**Guardrail — return rate.** Real baseline **14.8%**. A reco that pushes irrelevant items
can lift attach rate while inflating returns; the guardrail catches that.

## Sample sizing (α = 0.05 one-sided, power = 80%)

| Metric | MDE | n per arm |
|---|---|---|
| Attach rate (primary) | 8.1% → 9.7% (+20% rel) | **3,817** |
| AOV (raw) | +3% rel | 170,853 |
| AOV (with CUPED, ρ=0.5) | +3% rel | 128,140 (−25%) |

The 45× gap between the two is the whole argument for making attach rate the primary
metric. (Numbers reproduced by `src/experiment.py` from live warehouse baselines.)

**Duration.** At this dataset's ~2,000 orders/month, ~7,600 exposed orders would take
months — a red flag that *this* business lacks the traffic to test small effects quickly.
In a product-company setting (orders/day in the thousands) the same design reads in days.
Worth stating explicitly: it shows you reason about feasibility, not just formulas.

## Analysis plan (pre-registered)

- **Primary:** two-proportion z-test, one-sided (we only ship a positive lift).
- **AOV:** Welch's t-test on `log(AOV)` (handles the skew), or CUPED-adjusted means.
- **No peeking:** fixed horizon, or a sequential test (e.g. always-valid p-values) if we
  want to monitor — naive daily peeking inflates the false-positive rate well past 5%.
- **Multiple metrics:** primary is pre-declared; secondaries are directional only.

## Decision rule (pre-registered)

> **Ship** iff the primary (attach rate) shows a significant positive lift **and** the
> returns guardrail is not significantly worse. A significant attach lift with a breached
> guardrail → **hold and investigate**. No significant primary effect → **do not ship**.

## Threats to validity

- **Novelty effect** — early lift may fade; run long enough to see steady state.
- **Interference (SUTVA)** — if recommendations shift inventory/popularity, arms aren't
  independent; monitor for spillover.
- **Skew** — never run a raw-mean t-test on AOV without transformation or CUPED.
- **Simpson's paradox** — check the effect holds within key segments (new vs returning),
  not just in aggregate.

## Run it

```bash
python src/experiment.py
```

Reads live baselines, sizes both metrics, validates the design via Monte Carlo
(empirical power ≈ 80%, false-positive ≈ 5%), and applies the decision rule to a
simulated readout.
