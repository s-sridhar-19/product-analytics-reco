# 🛍️ Product Analytics & Recommendation Engine

An analytics-engineering project that turns **540K+ raw e-commerce transactions** into customer segments, retention cohorts, a market-basket recommender, and a statistically-designed cross-sell experiment — modelled on a **DuckDB + dbt medallion warehouse** and delivered through an interactive **Tableau** dashboard.

> 📊 **Live dashboard:** _Tableau Public link to be added once published_
> 💾 **Dataset:** UCI Online Retail (public) — 541,909 real UK e-commerce transactions, Dec 2010 – Dec 2011

---

## 🎯 Business Intent & Core Value

A retailer with one transactional table and no analytics layer cannot answer the three questions that actually move revenue. This project builds the layer that answers them:

* **Who is worth keeping?** — RFM segmentation that quantifies the value concentration across the customer base (spoiler: a fifth of customers drive most of the money).
* **Are we keeping them?** — Monthly cohort retention that shows how quickly first-time buyers lapse, so lifecycle effort targets the right window.
* **What should we recommend, and is it worth it?** — A market-basket affinity recommender that surfaces high-confidence cross-sell pairs, paired with a **designed A/B test** so the business can prove a lift before rolling it out — not guess.

The output is an analytics-ready **Gold** layer and a decision-oriented dashboard, not just a chart pack.

---

## 🏗️ System Architecture & Data Flow

A single raw CSV is transformed into clean, tested business marts through a medallion warehouse, then forked into two consumers: a BI dashboard and an experiment design.

```text
  ┌────────────────────────┐
  │  UCI Online Retail CSV │  ──► 541,909 raw UK e-commerce transactions
  └────────────────────────┘
             │
             ▼ [ ingest.py + profiling gate ]
  ┌────────────────────────┐
  │   DuckDB · RAW schema  │  ──► Faithful, all-VARCHAR landing copy + ingest metadata
  └────────────────────────┘
             │
             ▼ [ dbt · staging ]
  ┌────────────────────────┐
  │  STAGING (typed views) │  ──► Casts types, adds data-quality flags, keeps every row
  └────────────────────────┘
             │
             ▼ [ dbt · intermediate ]
  ┌────────────────────────┐
  │  INT · order lines     │  ──► Applies business rules (541,909 → 396,337 clean lines)
  └────────────────────────┘
             │
             ▼ [ dbt · marts ]
  ┌────────────────────────┐
  │  MARTS (Gold layer)    │  ──► KPIs · RFM · Cohorts · Affinity · Reco · Cross-sell
  └────────────────────────┘
        │                              │
        ▼ export_for_tableau.py        ▼ experiment.py
  ┌──────────────────────┐    ┌──────────────────────────┐
  │  Tableau Dashboard   │    │  A/B Test Design         │
  │  (interactive BI)    │    │  (power + CUPED + MC sim) │
  └──────────────────────┘    └──────────────────────────┘
```

---

## 🗂️ Warehouse Topography (Medallion)

| Layer | Schema | Object Type | Transformation Purpose |
| :--- | :--- | :--- | :--- |
| **Bronze** | `raw` | Table | Lands the source CSV faithfully as all-VARCHAR with ingest metadata — an immutable, auditable copy of what arrived. |
| **Silver** | `staging` | View | Casts data types and attaches data-quality flags (cancellations, non-positive qty/price, missing customer) **without dropping any rows**. |
| **Silver** | `intermediate` | View | Applies the business rules against the flags to produce clean order lines (`int_order_lines`) — every excluded row is traceable to a rule. |
| **Gold** | `marts` | Tables | Final analytical marts that power BI and the experiment: revenue KPIs, RFM segments, cohort retention, product affinity, recommendations, and cross-sell opportunity. |

**Gold marts:** `mart_revenue_kpis` · `mart_rfm_segments` · `mart_cohort_retention` · `mart_product_affinity` · `mart_recommendations` · `mart_crosssell_opportunity`

---

## 🛠️ Engineering Complexities & Core Triumphs

### 1. Non-Deterministic RFM Scoring (the headline fix)
* **The Complexity:** RFM quintiles were originally assigned with `ntile(5)`. Because many customers share identical frequency values, `ntile` split those ties by row order — which is not stable across runs or machines. The consequence was silent and serious: segment membership shifted between runs, so the flagship insight *"Champions = X% of revenue"* changed every time the project was rebuilt. A portfolio metric you can't reproduce is a metric you can't defend in an interview.
* **The Resolution:** Replaced rank-based `ntile` with **value-based `percent_rank` quintiles**, making each customer's score a pure function of their data rather than their position in the table. Results now reproduce bit-for-bit across runs and machines — **891 Champions driving 63.5% of revenue, every time.**

### 2. Filtering Messy Retail Data Without Losing Auditability
* **The Complexity:** Real retail data is dirty — cancellations, returns, zero/negative prices, and ~24.9% of rows missing a customer ID. Scrubbing at ingest would have made the pipeline opaque: you couldn't later prove *why* a row vanished.
* **The Resolution:** Quality is **flagged in staging, enforced in intermediate**. Staging keeps all 541,909 rows with boolean quality flags; the intermediate model applies the business filter down to 396,337 clean order lines. Every dropped row maps to an explicit, documented rule.

### 3. Warehouse-Portable Modelling (DuckDB dev → BigQuery prod)
* **The Complexity:** Cloud warehouses cost money and slow iteration, but a portfolio that only runs on a laptop reads as a toy.
* **The Resolution:** The same dbt project runs on **DuckDB locally** (zero cost, sub-second iteration) and targets **BigQuery for production** via `profiles.yml`. The ~7 dialect-specific functions that differ between engines are documented in `docs/DBT_BIGQUERY.md`, so the cloud port is an explicit, costed step — not a surprise.

### 4. Recommendations That Survive Scrutiny
* **The Complexity:** Ranking co-purchase pairs by **lift alone** surfaces rare, low-volume pairs — statistically eye-catching but commercially worthless.
* **The Resolution:** The affinity marts carry **support (basket frequency) alongside lift**, so recommendations are both significant *and* worth acting on. The cross-sell mart sizes the opportunity with a realistic-capture view rather than only the 100%-capture ceiling.

---

## 🧪 From Insight to Action: A Designed Experiment

A recommender produces candidates; it doesn't prove they work. `experiment.py` and `docs/EXPERIMENT_DESIGN.md` specify a two-arm A/B test to close that gap:

* **Primary metric — attach rate** (recommended-item adds per session): a low-variance, decision-relevant metric requiring **~3,817 customers per arm** for 80% power at a realistic minimum detectable effect.
* **AOV was evaluated and rejected as the primary** — far too high-variance (it would need ~128K per arm even after CUPED variance reduction), a deliberate trade-off rather than an oversight.
* **Validated by Monte Carlo simulation** at **79.5% power** and a **4.9% false-positive rate**, with baselines read directly from the warehouse.

> **Honest scope:** the experiment's *outcomes* are simulated on 2011 data — the deliverable is the **methodology and power analysis**, the part that demonstrates causal-inference judgement, not a fabricated lift number.

---

## 📈 Key Findings

* **£8.76M** revenue · **18,402** orders · **4,334** customers · **£476** average order value (Dec 2010 – Dec 2011).
* **Revenue concentration:** roughly a fifth of customers (891 "Champions") generate **63.5% of revenue** — the central argument for a retention-first strategy.
* **Retention cliff:** repeat-purchase rate drops sharply after the first month, pinpointing where lifecycle intervention pays off.
* **Cross-sell signal:** the strongest co-purchase pairs (by lift, filtered for support) drive the recommender and a sized, realistic cross-sell opportunity.

---

## 🚀 Technical Stack Summary

* **Source Data:** UCI Online Retail (public dataset)
* **Warehouse:** DuckDB (local dev) · BigQuery-ready (production target)
* **Modelling & Tests:** dbt Core (`dbt-duckdb`) — medallion architecture, 21-node build, 13 tests
* **Ingestion & Glue:** Python 3 (`duckdb`, `pandas`) with a pre-load profiling gate
* **Experimentation:** NumPy Monte Carlo power simulation + CUPED variance reduction
* **BI / Visualisation:** Tableau (interactive dashboard — KPIs, revenue trend, RFM treemap, cohort heatmap, affinity bars, interactive reco lookup, cross-sell opportunity)
