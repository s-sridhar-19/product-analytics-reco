-- Serving layer: top-5 complements per product (both directions of each pair).
WITH bidirectional AS (
    SELECT antecedent AS product, antecedent_desc AS product_desc,
           consequent AS recommended, consequent_desc AS recommended_desc, confidence, lift
    FROM {{ ref('mart_product_affinity') }}
    UNION ALL
    SELECT consequent, consequent_desc, antecedent, antecedent_desc, confidence, lift
    FROM {{ ref('mart_product_affinity') }}
),
ranked AS (
    SELECT *, row_number() OVER (PARTITION BY product ORDER BY lift DESC, confidence DESC) AS rec_rank
    FROM bidirectional
)
SELECT product, product_desc, recommended, recommended_desc, lift, confidence, rec_rank
FROM ranked WHERE rec_rank <= 5 ORDER BY product, rec_rank
