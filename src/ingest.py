"""
Ingestion: load the raw Online Retail CSV into the DuckDB warehouse `raw` layer.

Design choices (best practice):
- The raw layer is a *faithful* copy of the source. No cleaning here — every column
  lands as VARCHAR so we never lose or silently coerce data. All typing/cleaning is
  pushed downstream into the staging models, which keeps the pipeline auditable.
- Idempotent: re-running rebuilds the raw table from source.
- Emits a lightweight data profile (row counts, null rates, date range) so ingestion
  failures or source drift are caught immediately, not three models later.
"""
from __future__ import annotations

import logging
import pathlib

import duckdb

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s"
)
log = logging.getLogger("ingest")

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "online_retail.csv"
DB_PATH = ROOT / "data" / "warehouse" / "retail.duckdb"


def ingest() -> None:
    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"Source CSV not found at {RAW_CSV}. "
            "Download it (see README) into data/raw/ before running."
        )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    log.info("Loading raw CSV -> raw.online_retail (all columns as VARCHAR)")
    con.execute("CREATE SCHEMA IF NOT EXISTS raw;")
    con.execute(
        """
        CREATE OR REPLACE TABLE raw.online_retail AS
        SELECT *
        FROM read_csv_auto(?, all_varchar = true, header = true);
        """,
        [str(RAW_CSV)],
    )

    # --- Profiling: fail loud if the source looks wrong ---
    n_rows = con.execute("SELECT count(*) FROM raw.online_retail").fetchone()[0]
    profile = con.execute(
        """
        SELECT
            count(*)                                              AS rows,
            count(DISTINCT InvoiceNo)                             AS invoices,
            count(DISTINCT CustomerID)                            AS customers,
            round(100.0 * count(*) FILTER (WHERE CustomerID IS NULL)
                  / count(*), 2)                                  AS pct_null_customer,
            min(InvoiceDate)                                      AS min_date,
            max(InvoiceDate)                                      AS max_date
        FROM raw.online_retail;
        """
    ).fetchone()

    if n_rows == 0:
        raise ValueError("Raw table is empty after load — check the source file.")

    log.info("Ingested %s rows", f"{profile[0]:,}")
    log.info("  distinct invoices : %s", f"{profile[1]:,}")
    log.info("  distinct customers: %s", f"{profile[2]:,}")
    log.info("  null CustomerID   : %s%%", profile[3])
    log.info("  date range (raw)  : %s -> %s", profile[4], profile[5])
    log.info("Done. Warehouse at %s", DB_PATH)
    con.close()


if __name__ == "__main__":
    ingest()
