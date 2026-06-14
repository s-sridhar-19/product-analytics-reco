-- Every stored pair must be a positive association.
SELECT * FROM {{ ref('mart_product_affinity') }} WHERE lift <= 1
