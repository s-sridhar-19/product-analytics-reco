-- Market-basket analysis: support / confidence / lift for co-purchased pairs.
-- lift > 1 = a genuine positive association (beyond independence).
WITH baskets AS (
    SELECT DISTINCT invoice_no, stock_code FROM {{ ref('int_order_lines') }}
),
item_support AS (
    SELECT stock_code, count(DISTINCT invoice_no) AS item_baskets FROM baskets GROUP BY 1
),
totals AS (SELECT count(DISTINCT invoice_no) AS n_baskets FROM baskets),
pairs AS (
    SELECT a.stock_code AS antecedent, b.stock_code AS consequent, count(*) AS pair_baskets
    FROM baskets a JOIN baskets b
      ON a.invoice_no = b.invoice_no AND a.stock_code < b.stock_code
    GROUP BY 1, 2 HAVING count(*) >= 25
),
labels AS (
    SELECT stock_code, any_value(description) AS description
    FROM {{ ref('int_order_lines') }} GROUP BY 1
)
SELECT
    p.antecedent, la.description AS antecedent_desc,
    p.consequent, lc.description AS consequent_desc,
    p.pair_baskets,
    round(p.pair_baskets::DOUBLE / t.n_baskets, 4)              AS support,
    round(p.pair_baskets::DOUBLE / ia.item_baskets, 3)         AS confidence,
    round((p.pair_baskets::DOUBLE / ia.item_baskets)
          / (ic.item_baskets::DOUBLE / t.n_baskets), 2)        AS lift
FROM pairs p
JOIN item_support ia ON p.antecedent = ia.stock_code
JOIN item_support ic ON p.consequent = ic.stock_code
JOIN labels la ON p.antecedent = la.stock_code
JOIN labels lc ON p.consequent = lc.stock_code
CROSS JOIN totals t
WHERE round((p.pair_baskets::DOUBLE / ia.item_baskets)
      / (ic.item_baskets::DOUBLE / t.n_baskets), 2) > 1
ORDER BY lift DESC
