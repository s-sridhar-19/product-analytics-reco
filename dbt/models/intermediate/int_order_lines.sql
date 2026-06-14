-- The clean "valid sale" grain. Each filter = one named business rule.
SELECT
    invoice_no, stock_code, description, quantity, unit_price, line_revenue,
    customer_id, country, invoice_ts,
    CAST(date_trunc('month', invoice_ts) AS DATE)   AS invoice_month
FROM {{ ref('stg_transactions') }}
WHERE NOT is_cancellation
  AND NOT is_guest
  AND NOT is_non_product
  AND quantity > 0
  AND unit_price > 0
  AND line_revenue > 0
