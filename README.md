# Product Analytics & Recommendation Engine

An end-to-end analytics project over **541,909 real e-commerce transactions** that does
three things a product/growth team pays for:

1. **Understand the customers** — RFM segmentation, cohort retention, revenue concentration.
2. **Recommend what's next** — market-basket affinity to an item-to-item recommender.
3. **Prove it works** — a designed + power-analysed A/B test for whether the recommender
   *causally* lifts attach rate (not just that products co-occur).

Built as a *data-analyst project with real data-engineering underneath*: an EL load, a
layered **dbt** transform project with tests, a Tableau serving layer, and an
experimentation module — not a one-off notebook.

## Architecture

```
raw CSV --ingest.py--> raw.online_retail        (faithful copy, all VARCHAR)
                            |
                    dbt (transform + test)
                            |
                   stg_transactions   (view: type + flag)
                            |
                   int_order_lines    (table: business-rule filtering)
                            |
   revenue_kpis / rfm_segments / cohort_retention / product_affinity
                            |                              |
                            |                       recommendations --> crosssell_opportunity
              export_for_tableau.py            experiment.py
              (CSVs -> Tableau Public)         (A/B test design + simulation)
```

Transforms run through **dbt** (dev = DuckDB locally, prod = BigQuery). Layering and
lineage port directly to BigQuery; a few SQL functions need dialect tweaks — see
`docs/DBT_BIGQUERY.md` (kept honest, no "zero rewrite" claims).

## Stack

- **DuckDB** — local analytical warehouse (BigQuery-compatible SQL)
- **dbt** — layered transforms + data-quality tests (13 tests, all passing)
- **Python / scipy / statsmodels** — the experimentation layer
- **Tableau Public** — recruiter-facing dashboard (see `docs/TABLEAU_GUIDE.md`)

## Run it

```bash
pip install -r requirements.txt

python src/ingest.py                              # 1. load source -> raw layer
cd dbt && DBT_PROFILES_DIR=. dbt build && cd ..   # 2. build + test marts
python src/export_for_tableau.py                  # 3. Tableau-ready CSVs
python src/experiment.py                          # 4. size + simulate the A/B test
# or just: make all
```

> **Data:** `data/raw/online_retail.csv` is git-ignored. Download from the
> UCI repository (http://archive.ics.uci.edu/dataset/352/online+retail) into `data/raw/`.

## Sample insights (real data)

- **Revenue is concentrated:** Champions are ~22% of customers but ~65% of revenue.
- **The recommender finds real complements:** JUMBO BAG RED RETROSPOT -> other jumbo bags
  at 6-7x lift.
- **Retention decays:** the Dec-2010 cohort holds ~38% at month 3; later cohorts ~20%.
- **Causal honesty:** attach rate needs only ~3,800/arm to test, but AOV needs ~171k
  (->128k with CUPED) — so attach rate is the primary metric, AOV the noisier north-star.

## Repo layout

```
src/
  ingest.py              EL: raw CSV -> DuckDB raw layer (+ profiling)
  export_for_tableau.py  marts -> Tableau CSVs
  experiment.py          A/B test sizing, Monte-Carlo validation, decision rule
dbt/
  models/staging|intermediate|marts/   layered SQL models
  tests/                 custom singular data-quality tests
  profiles.yml           dev=DuckDB, prod=BigQuery
docs/
  EXPERIMENT_DESIGN.md   the causal-reasoning writeup
  DBT_BIGQUERY.md        cloud deployment guide (honest portability notes)
  TABLEAU_GUIDE.md       dashboard build + publish guide
data/raw|warehouse/      source CSV + DuckDB file (git-ignored)
```
