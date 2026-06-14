-- Monthly acquisition cohorts and their retention curve.
WITH cohorts AS (
    SELECT customer_id, min(invoice_month) AS cohort_month
    FROM {{ ref('int_order_lines') }} GROUP BY 1
),
activity AS (
    SELECT DISTINCT ol.customer_id, c.cohort_month, ol.invoice_month AS active_month,
           date_diff('month', c.cohort_month, ol.invoice_month) AS months_since
    FROM {{ ref('int_order_lines') }} ol JOIN cohorts c USING (customer_id)
),
cohort_size AS (SELECT cohort_month, count(*) AS cohort_customers FROM cohorts GROUP BY 1)
SELECT a.cohort_month, cs.cohort_customers, a.months_since,
       count(DISTINCT a.customer_id) AS active_customers,
       round(100.0 * count(DISTINCT a.customer_id) / cs.cohort_customers, 1) AS retention_rate_pct
FROM activity a JOIN cohort_size cs USING (cohort_month)
GROUP BY a.cohort_month, cs.cohort_customers, a.months_since
ORDER BY a.cohort_month, a.months_since
