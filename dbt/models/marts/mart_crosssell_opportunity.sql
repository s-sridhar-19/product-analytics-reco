-- ADDRESSABLE cross-sell opportunity (ASSOCIATION, not proven causal lift).
-- For strong pairs (lift >= 3): orders that bought the antecedent but NOT the
-- consequent = where a "frequently bought together" nudge *could* apply. The
-- revenue figure is a gross ceiling (100% capture); src/experiment.py sizes the
-- realistic, causally-tested capture rate.
WITH strong_pairs AS (
    SELECT antecedent, consequent, lift
    FROM {{ ref('mart_product_affinity') }} WHERE lift >= 3
),
baskets AS (SELECT DISTINCT invoice_no, stock_code FROM {{ ref('int_order_lines') }}),
avg_price AS (
    SELECT stock_code, avg(unit_price) AS price, any_value(description) AS description
    FROM {{ ref('int_order_lines') }} GROUP BY 1
),
opportunity AS (
    SELECT sp.antecedent, sp.consequent, sp.lift, b.invoice_no
    FROM strong_pairs sp
    JOIN baskets b  ON b.stock_code = sp.antecedent
    LEFT JOIN baskets b2 ON b2.invoice_no = b.invoice_no AND b2.stock_code = sp.consequent
    WHERE b2.stock_code IS NULL
)
SELECT
    o.consequent                       AS recommend_code,
    ap.description                     AS recommend_desc,
    count(*)                           AS missed_baskets,
    round(avg(o.lift), 1)              AS avg_lift,
    round(count(*) * avg(ap.price), 2) AS gross_revenue_ceiling
FROM opportunity o JOIN avg_price ap ON o.consequent = ap.stock_code
GROUP BY 1, 2 ORDER BY gross_revenue_ceiling DESC
