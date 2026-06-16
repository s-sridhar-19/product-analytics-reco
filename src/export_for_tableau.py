"""
Export the marts to clean, Tableau-ready CSVs.

Tableau Public can't connect to DuckDB directly — it reads file extracts. This
step writes one tidy CSV per view, shaped for the specific chart it feeds
(e.g. cohort retention stays long/tidy for a heatmap). Run it after the
transform layer; the CSVs in `tableau_exports/` are what you connect Tableau to.
"""
from __future__ import annotations

import logging
import pathlib

import duckdb

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
log = logging.getLogger("export")

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "warehouse" / "retail.duckdb"
OUT = ROOT / "tableau_exports"

# name -> SQL feeding each Tableau sheet
EXPORTS = {
    "revenue_kpis": "SELECT * FROM analytics.mart_revenue_kpis ORDER BY invoice_month",
    "rfm_customers": "SELECT * FROM analytics.mart_rfm_segments",
    "rfm_segment_summary": """
        SELECT segment,
               count(*)                                   AS customers,
               round(sum(monetary), 2)                    AS total_revenue,
               round(100.0 * sum(monetary)
                     / sum(sum(monetary)) OVER (), 1)      AS pct_of_revenue,
               round(avg(recency_days), 1)                AS avg_recency_days,
               round(avg(frequency), 1)                   AS avg_frequency
        FROM analytics.mart_rfm_segments
        GROUP BY 1
        ORDER BY total_revenue DESC
    """,
    "cohort_retention": "SELECT * FROM analytics.mart_cohort_retention "
                        "ORDER BY cohort_month, months_since",
    "recommendations": "SELECT * FROM analytics.mart_recommendations "
                       "ORDER BY product, rec_rank",
    "top_affinity": "SELECT antecedent_desc, consequent_desc, pair_baskets, "
                    "support, confidence, lift FROM analytics.mart_product_affinity "
                    "ORDER BY lift DESC LIMIT 200",
    "crosssell_opportunity": (
        "SELECT recommend_desc, missed_baskets, avg_lift, gross_revenue_ceiling "
        "FROM analytics.mart_crosssell_opportunity "
        "ORDER BY gross_revenue_ceiling DESC LIMIT 15"
    )
}


def export() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    for name, sql in EXPORTS.items():
        path = OUT / f"{name}.csv"
        con.execute(
            f"COPY ({sql}) TO '{path}' (FORMAT CSV, HEADER, DELIMITER ',');"
        )
        n = con.execute(f"SELECT count(*) FROM ({sql})").fetchone()[0]
        log.info("Wrote %-22s %s rows", name + ".csv", f"{n:,}")
    con.close()
    log.info("Tableau exports ready in %s", OUT)


if __name__ == "__main__":
    export()
