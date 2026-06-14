-- RFM scoring (quintiles) -> named, actionable segments. Recency is reversed
-- (recent buyers score high). Quintiles are distribution-relative, so the model
-- adapts to any dataset instead of relying on hard-coded thresholds.
WITH snapshot AS (
    SELECT max(invoice_ts) + INTERVAL 1 DAY AS as_of FROM {{ ref('int_order_lines') }}
),
customer_rfm AS (
    SELECT ol.customer_id,
           date_diff('day', max(ol.invoice_ts), s.as_of) AS recency_days,
           count(DISTINCT ol.invoice_no)                 AS frequency,
           round(sum(ol.line_revenue), 2)                AS monetary
    FROM {{ ref('int_order_lines') }} ol CROSS JOIN snapshot s
    GROUP BY ol.customer_id, s.as_of
),
scored AS (
    -- Value-based quintiles via percent_rank: identical R/F/M values always get
    -- identical scores, and the result is reproducible across runs/engines
    -- (percent_rank assigns ties the same rank). This replaces ntile(5), which
    -- forced equal-sized buckets and split tied values nondeterministically.
    -- Recency is ranked DESC so the most recent buyers (lowest recency) score 5.
    SELECT *,
        greatest(1, least(5, ceil(percent_rank() OVER (ORDER BY recency_days DESC) * 5)))::INT AS r_score,
        greatest(1, least(5, ceil(percent_rank() OVER (ORDER BY frequency)        * 5)))::INT AS f_score,
        greatest(1, least(5, ceil(percent_rank() OVER (ORDER BY monetary)         * 5)))::INT AS m_score
    FROM customer_rfm
)
SELECT customer_id, recency_days, frequency, monetary,
       r_score, f_score, m_score, (r_score + f_score + m_score) AS rfm_total,
       CASE
           WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
           WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
           WHEN r_score >= 4 AND f_score <= 2                  THEN 'New / Promising'
           WHEN r_score <= 2 AND f_score >= 4                  THEN 'At Risk (high value)'
           WHEN r_score <= 2 AND f_score <= 2 AND m_score >= 4 THEN 'Cannot Lose Them'
           WHEN r_score <= 2 AND f_score <= 2                  THEN 'Hibernating / Lost'
           ELSE 'Needs Attention'
       END AS segment
FROM scored ORDER BY monetary DESC
