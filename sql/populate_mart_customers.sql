-- Populate mart.customers with sample data
-- Add 300+ customers with NULL emails (for null spike scenario) and some with valid emails

-- Clear existing data
TRUNCATE TABLE mart.customers;

-- Insert 300 customers with mixed email status
INSERT INTO mart.customers (customer_id, customer_name, first_order_date, most_recent_order_date, number_of_orders, lifetime_spend, customer_email)
SELECT 
    generate_series AS customer_id,
    'Customer ' || generate_series AS customer_name,
    '2024-01-01'::date + (random() * 90)::int AS first_order_date,
    '2024-03-01'::date + (random() * 30)::int AS most_recent_order_date,
    (random() * 10 + 1)::int AS number_of_orders,
    (random() * 1000 + 50)::numeric(10,2) AS lifetime_spend,
    CASE 
        WHEN random() < 0.4 THEN NULL  -- 40% null emails (null spike scenario)
        ELSE 'customer' || generate_series || '@example.com'
    END AS customer_email
FROM generate_series(1, 300);

-- Verify data
SELECT 
    'Total customers:' as info, 
    COUNT(*) as count 
FROM mart.customers
UNION ALL
SELECT 
    'NULL customer_email:', 
    COUNT(*) 
FROM mart.customers 
WHERE customer_email IS NULL
UNION ALL
SELECT 
    'Non-NULL customer_email:', 
    COUNT(*) 
FROM mart.customers 
WHERE customer_email IS NOT NULL;
