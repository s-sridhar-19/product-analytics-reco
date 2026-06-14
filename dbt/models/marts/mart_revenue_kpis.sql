-- Monthly business health: revenue, orders, active customers, AOV, new vs returning.
WITH first_order AS (
    SELECT customer_id, min(invoice_month) AS cohort_month
    FROM {{ ref('int_order_lines') }} GROUP BY 1
),
orders AS (
    SELECT ol.invoice_month, ol.invoice_no, ol.customer_id,
           sum(ol.line_revenue) AS order_revenue,
           (ol.invoice_month = fo.cohort_month) AS is_new_customer
    FROM {{ ref('int_order_lines') }} ol
    JOIN first_order fo USING (customer_id)
    GROUP BY 1, 2, 3, fo.cohort_month
)
SELECT
    invoice_month,
    round(sum(order_revenue), 2)                                AS revenue,
    count(DISTINCT invoice_no)                                  AS orders,
    count(DISTINCT customer_id)                                 AS active_customers,
    round(sum(order_revenue) / count(DISTINCT invoice_no), 2)   AS avg_order_value,
    count(DISTINCT customer_id) FILTER (WHERE is_new_customer)  AS new_customers,
    count(DISTINCT customer_id) FILTER (WHERE NOT is_new_customer) AS returning_customers
FROM orders GROUP BY 1 ORDER BY 1
