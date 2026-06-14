SELECT product FROM {{ ref('mart_recommendations') }}
GROUP BY product HAVING count(*) > 5
