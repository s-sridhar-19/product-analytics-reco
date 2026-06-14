-- A cohort's month-0 retention is 100% by definition.
SELECT * FROM {{ ref('mart_cohort_retention') }}
WHERE months_since = 0 AND retention_rate_pct <> 100
