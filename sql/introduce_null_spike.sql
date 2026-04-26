-- Introduce Null Spike (without fix)
-- This creates a data quality failure for AI SDK to detect

-- Step 1: Ensure customer_email column exists
ALTER TABLE staging.stg_customers ADD COLUMN IF NOT EXISTS customer_email TEXT;
ALTER TABLE mart.customers ADD COLUMN IF NOT EXISTS customer_email TEXT;

-- Step 2: Populate customer_email initially if null
UPDATE staging.stg_customers 
SET customer_email = LOWER(REPLACE(customer_name, ' ', '.')) || '@jaffleshop.com'
WHERE customer_email IS NULL;

-- Step 3: Introduce nulls in staging (40% of records)
UPDATE staging.stg_customers
SET customer_email = NULL
WHERE customer_id IN (
    SELECT customer_id FROM staging.stg_customers
    ORDER BY RANDOM()
    LIMIT (SELECT CAST(COUNT(*) * 0.4 AS INTEGER) FROM staging.stg_customers)
);

-- Step 4: Re-populate mart from staging (propagates the nulls)
DELETE FROM mart.order_items WHERE order_id IN (SELECT order_id FROM mart.orders);
DELETE FROM mart.orders;
DELETE FROM mart.customers;

INSERT INTO mart.customers
SELECT 
    c.customer_id,
    c.customer_name,
    MIN(o.ordered_at) as first_order_date,
    MAX(o.ordered_at) as most_recent_order_date,
    COUNT(DISTINCT o.order_id) as number_of_orders,
    SUM(o.order_total) as lifetime_spend,
    s.customer_email
FROM staging.stg_orders o
JOIN staging.stg_customers c ON o.customer_id = c.customer_id
JOIN staging.stg_customers s ON c.customer_id = s.customer_id
GROUP BY c.customer_id, c.customer_name, s.customer_email;

-- Verify issue state
SELECT 'Null count in staging:' as info, COUNT(*) as null_count, 
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM staging.stg_customers), 2) as null_percentage
FROM staging.stg_customers WHERE customer_email IS NULL
UNION ALL
SELECT 'Null count in mart:', COUNT(*), 
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM mart.customers), 2)
FROM mart.customers WHERE customer_email IS NULL;
