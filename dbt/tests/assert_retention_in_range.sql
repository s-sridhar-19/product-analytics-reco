SELECT * FROM {{ ref('mart_cohort_retention') }}
WHERE retention_rate_pct < 0 OR retention_rate_pct > 100
