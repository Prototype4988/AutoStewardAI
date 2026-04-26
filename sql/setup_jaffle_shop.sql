-- Jaffle Shop Database Setup for AutoSteward AI
-- This script creates the Jaffle Shop database schema and loads the CSV seed data
-- Note: Database must already exist. Run: DROP DATABASE IF EXISTS jaffle_shop; CREATE DATABASE jaffle_shop;

-- Create raw schema for source data
CREATE SCHEMA IF NOT EXISTS raw;

-- Create staging schema for transformed data
CREATE SCHEMA IF NOT EXISTS staging;

-- Create mart schema for business logic
CREATE SCHEMA IF NOT EXISTS mart;

-- Create raw tables
CREATE TABLE raw.raw_customers (
    id TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE raw.raw_orders (
    id TEXT PRIMARY KEY,
    customer TEXT,
    ordered_at TIMESTAMP,
    store_id TEXT,
    subtotal INT,
    tax_paid INT,
    order_total INT
);

CREATE TABLE raw.raw_order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT,
    sku TEXT
);

CREATE TABLE raw.raw_products (
    sku TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    price INT,
    description TEXT
);

CREATE TABLE raw.raw_supplies (
    id TEXT PRIMARY KEY,
    name TEXT,
    cost INT,
    perishable BOOLEAN,
    sku TEXT
);

CREATE TABLE raw.raw_stores (
    id TEXT PRIMARY KEY,
    name TEXT,
    opened_at TIMESTAMP,
    tax_rate FLOAT
);

-- Load CSV data into raw tables
-- Note: COPY commands need to be run with psql -c or from within psql
-- Copy the CSV files from /tmp/jaffle-data/

\copy raw.raw_customers FROM '/tmp/jaffle-data/raw_customers.csv' DELIMITER ',' CSV HEADER;
\copy raw.raw_orders FROM '/tmp/jaffle-data/raw_orders.csv' DELIMITER ',' CSV HEADER;
\copy raw.raw_order_items FROM '/tmp/jaffle-data/raw_items.csv' DELIMITER ',' CSV HEADER;
\copy raw.raw_products FROM '/tmp/jaffle-data/raw_products.csv' DELIMITER ',' CSV HEADER;
\copy raw.raw_supplies FROM '/tmp/jaffle-data/raw_supplies.csv' DELIMITER ',' CSV HEADER;
\copy raw.raw_stores FROM '/tmp/jaffle-data/raw_stores.csv' DELIMITER ',' CSV HEADER;

-- Create staging tables
CREATE TABLE staging.stg_customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT
);

CREATE TABLE staging.stg_orders (
    order_id TEXT PRIMARY KEY,
    location_id TEXT,
    customer_id TEXT,
    subtotal_cents INT,
    tax_paid_cents INT,
    order_total_cents INT,
    subtotal NUMERIC(10,2),
    tax_paid NUMERIC(10,2),
    order_total NUMERIC(10,2),
    ordered_at DATE
);

CREATE TABLE staging.stg_order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT,
    sku TEXT
);

CREATE TABLE staging.stg_products (
    sku TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    price_cents INT,
    price NUMERIC(10,2),
    description TEXT
);

CREATE TABLE staging.stg_supplies (
    id TEXT PRIMARY KEY,
    name TEXT,
    cost_cents INT,
    cost NUMERIC(10,2),
    perishable BOOLEAN,
    sku TEXT
);

CREATE TABLE staging.stg_locations (
    location_id TEXT PRIMARY KEY,
    location_name TEXT,
    opened_at DATE,
    tax_rate NUMERIC(5,4)
);

-- Populate staging tables from raw tables
INSERT INTO staging.stg_customers
SELECT 
    id as customer_id,
    name as customer_name
FROM raw.raw_customers;

INSERT INTO staging.stg_orders
SELECT 
    id as order_id,
    store_id as location_id,
    customer as customer_id,
    subtotal as subtotal_cents,
    tax_paid as tax_paid_cents,
    order_total as order_total_cents,
    subtotal / 100.0 as subtotal,
    tax_paid / 100.0 as tax_paid,
    order_total / 100.0 as order_total,
    DATE_TRUNC('day', ordered_at) as ordered_at
FROM raw.raw_orders;

INSERT INTO staging.stg_order_items
SELECT 
    id,
    order_id,
    sku
FROM raw.raw_order_items;

INSERT INTO staging.stg_products
SELECT 
    sku,
    name,
    type,
    price as price_cents,
    price / 100.0 as price,
    description
FROM raw.raw_products;

INSERT INTO staging.stg_supplies
SELECT 
    id,
    name,
    cost as cost_cents,
    cost / 100.0 as cost,
    perishable,
    sku
FROM raw.raw_supplies;

INSERT INTO staging.stg_locations
SELECT 
    id as location_id,
    name as location_name,
    DATE_TRUNC('day', opened_at) as opened_at,
    tax_rate
FROM raw.raw_stores;

-- Create mart tables (simplified for demo)
CREATE TABLE mart.customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT,
    first_order_date DATE,
    most_recent_order_date DATE,
    number_of_orders INT,
    lifetime_spend NUMERIC(10,2)
);

CREATE TABLE mart.orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT,
    location_id TEXT,
    order_date DATE,
    subtotal NUMERIC(10,2),
    tax_paid NUMERIC(10,2),
    order_total NUMERIC(10,2)
);

CREATE TABLE mart.order_items (
    id TEXT PRIMARY KEY,
    order_id TEXT,
    sku TEXT,
    product_name TEXT,
    price NUMERIC(10,2)
);

CREATE TABLE mart.products (
    sku TEXT PRIMARY KEY,
    name TEXT,
    type TEXT,
    price NUMERIC(10,2),
    description TEXT
);

CREATE TABLE mart.locations (
    location_id TEXT PRIMARY KEY,
    location_name TEXT,
    opened_at DATE,
    tax_rate NUMERIC(5,4)
);

CREATE TABLE mart.supplies (
    id TEXT PRIMARY KEY,
    name TEXT,
    cost NUMERIC(10,2),
    perishable BOOLEAN,
    sku TEXT
);

-- Populate mart tables from staging tables
INSERT INTO mart.customers
SELECT 
    c.customer_id,
    c.customer_name,
    MIN(o.ordered_at) as first_order_date,
    MAX(o.ordered_at) as most_recent_order_date,
    COUNT(DISTINCT o.order_id) as number_of_orders,
    SUM(o.order_total) as lifetime_spend
FROM staging.stg_orders o
JOIN staging.stg_customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name;

INSERT INTO mart.orders
SELECT 
    order_id,
    customer_id,
    location_id,
    ordered_at as order_date,
    subtotal,
    tax_paid,
    order_total
FROM staging.stg_orders;

INSERT INTO mart.order_items
SELECT 
    oi.id,
    oi.order_id,
    oi.sku,
    p.name as product_name,
    p.price
FROM staging.stg_order_items oi
JOIN staging.stg_products p ON oi.sku = p.sku;

INSERT INTO mart.products
SELECT 
    sku,
    name,
    type,
    price,
    description
FROM staging.stg_products;

INSERT INTO mart.locations
SELECT 
    location_id,
    location_name,
    opened_at,
    tax_rate
FROM staging.stg_locations;

INSERT INTO mart.supplies
SELECT 
    id,
    name,
    cost,
    perishable,
    sku
FROM staging.stg_supplies;

-- Create indexes for performance
CREATE INDEX idx_mart_customers_customer_id ON mart.customers(customer_id);
CREATE INDEX idx_mart_orders_customer_id ON mart.orders(customer_id);
CREATE INDEX idx_mart_orders_order_date ON mart.orders(order_date);
CREATE INDEX idx_mart_order_items_order_id ON mart.order_items(order_id);
CREATE INDEX idx_mart_order_items_sku ON mart.order_items(sku);

-- Verify data
SELECT 'raw_customers count:' as info, COUNT(*) as count FROM raw.raw_customers
UNION ALL
SELECT 'raw_orders count:', COUNT(*) FROM raw.raw_orders
UNION ALL
SELECT 'raw_order_items count:', COUNT(*) FROM raw.raw_order_items
UNION ALL
SELECT 'raw_products count:', COUNT(*) FROM raw.raw_products
UNION ALL
SELECT 'raw_supplies count:', COUNT(*) FROM raw.raw_supplies
UNION ALL
SELECT 'raw_stores count:', COUNT(*) FROM raw.raw_stores
UNION ALL
SELECT 'stg_customers count:', COUNT(*) FROM staging.stg_customers
UNION ALL
SELECT 'stg_orders count:', COUNT(*) FROM staging.stg_orders
UNION ALL
SELECT 'stg_order_items count:', COUNT(*) FROM staging.stg_order_items
UNION ALL
SELECT 'stg_products count:', COUNT(*) FROM staging.stg_products
UNION ALL
SELECT 'stg_supplies count:', COUNT(*) FROM staging.stg_supplies
UNION ALL
SELECT 'stg_locations count:', COUNT(*) FROM staging.stg_locations
UNION ALL
SELECT 'mart_customers count:', COUNT(*) FROM mart.customers
UNION ALL
SELECT 'mart_orders count:', COUNT(*) FROM mart.orders
UNION ALL
SELECT 'mart_order_items count:', COUNT(*) FROM mart.order_items
UNION ALL
SELECT 'mart_products count:', COUNT(*) FROM mart.products
UNION ALL
SELECT 'mart_locations count:', COUNT(*) FROM mart.locations
UNION ALL
SELECT 'mart_supplies count:', COUNT(*) FROM mart.supplies;
