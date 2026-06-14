-- Typing + standardization. Flags bad rows but keeps all of them; filtering
-- happens in intermediate so every exclusion is auditable.
SELECT
    CAST(InvoiceNo AS VARCHAR)                                   AS invoice_no,
    CAST(StockCode AS VARCHAR)                                   AS stock_code,
    trim(Description)                                            AS description,
    CAST(Quantity AS INTEGER)                                    AS quantity,
    strptime(InvoiceDate, '%m/%d/%Y %H:%M')                      AS invoice_ts,
    CAST(UnitPrice AS DOUBLE)                                    AS unit_price,
    TRY_CAST(CustomerID AS BIGINT)                              AS customer_id,
    Country                                                      AS country,
    CAST(Quantity AS INTEGER) * CAST(UnitPrice AS DOUBLE)        AS line_revenue,
    upper(CAST(InvoiceNo AS VARCHAR)) LIKE 'C%'                  AS is_cancellation,
    CustomerID IS NULL                                           AS is_guest,
    upper(CAST(StockCode AS VARCHAR)) IN (
        'POST','DOT','M','C2','D','S','BANK CHARGES','AMAZONFEE',
        'CRUK','PADS','B','GIFT'
    ) OR upper(CAST(StockCode AS VARCHAR)) LIKE 'GIFT%'          AS is_non_product
FROM {{ source('raw', 'online_retail') }}
