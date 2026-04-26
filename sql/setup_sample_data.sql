-- AutoSteward AI - Sample Data Setup
-- Run this in your PostgreSQL database that OpenMetadata will connect to
-- Database is created by docker-compose POSTGRES_DB environment variable

-- Drop existing tables if they exist (for clean setup)
DROP TABLE IF EXISTS shipment_items CASCADE;
DROP TABLE IF EXISTS shipments CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS addresses CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS customers CASCADE;
DROP TABLE IF EXISTS legacy_inventory_logs CASCADE;

-- Create customers table
CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    date_of_birth DATE,
    tier VARCHAR(20) DEFAULT 'standard',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create addresses table
CREATE TABLE addresses (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    address_type VARCHAR(20) DEFAULT 'billing',
    street_address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    country VARCHAR(100) DEFAULT 'USA',
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create categories table
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    description TEXT,
    parent_category_id INTEGER REFERENCES categories(id),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create products table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES categories(id),
    sku VARCHAR(50) UNIQUE,
    name VARCHAR(255),
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    cost_price DECIMAL(10,2),
    stock_quantity INTEGER DEFAULT 0,
    low_stock_threshold INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create orders table
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    order_number VARCHAR(50) UNIQUE,
    status VARCHAR(50) DEFAULT 'pending',
    subtotal DECIMAL(10,2),
    tax DECIMAL(10,2) DEFAULT 0,
    shipping DECIMAL(10,2) DEFAULT 0,
    total DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    billing_address_id INTEGER REFERENCES addresses(id),
    shipping_address_id INTEGER REFERENCES addresses(id),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create order_items table
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_id INTEGER REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    total_price DECIMAL(10,2) GENERATED ALWAYS AS (quantity * unit_price - discount_amount) STORED,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create payments table
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    payment_method VARCHAR(50),
    payment_status VARCHAR(50) DEFAULT 'pending',
    amount DECIMAL(10,2),
    transaction_id VARCHAR(100),
    payment_date TIMESTAMP DEFAULT NOW()
);

-- Create shipments table
CREATE TABLE shipments (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    tracking_number VARCHAR(100),
    carrier VARCHAR(50),
    shipping_status VARCHAR(50) DEFAULT 'processing',
    shipped_at TIMESTAMP,
    delivered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create shipment_items table
CREATE TABLE shipment_items (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER REFERENCES shipments(id),
    order_item_id INTEGER REFERENCES order_items(id),
    quantity_shipped INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create legacy inventory logs table (for orphaned asset scenario)
CREATE TABLE legacy_inventory_logs (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(255),
    old_quantity INTEGER,
    new_quantity INTEGER,
    reason TEXT,
    logged_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Insert sample categories
INSERT INTO categories (name, description) VALUES
('Electronics', 'Electronic devices and accessories'),
('Clothing', 'Apparel and fashion items'),
('Home & Garden', 'Home improvement and garden supplies'),
('Sports', 'Sports equipment and accessories'),
('Books', 'Books and educational materials');

-- Insert sample products
INSERT INTO products (category_id, sku, name, description, price, cost_price, stock_quantity) VALUES
(1, 'ELEC-001', 'Wireless Bluetooth Headphones', 'High-quality wireless headphones with noise cancellation', 79.99, 45.00, 150),
(1, 'ELEC-002', 'USB-C Charging Cable', 'Fast charging cable for USB-C devices', 14.99, 3.00, 500),
(1, 'ELEC-003', 'Portable Power Bank', '10000mAh portable charger', 29.99, 15.00, 200),
(2, 'CLTH-001', 'Cotton T-Shirt', '100% cotton comfortable t-shirt', 19.99, 8.00, 300),
(2, 'CLTH-002', 'Denim Jeans', 'Classic fit denim jeans', 49.99, 25.00, 150),
(3, 'HOME-001', 'LED Desk Lamp', 'Adjustable LED desk lamp', 34.99, 18.00, 100),
(4, 'SPRT-001', 'Yoga Mat', 'Non-slip yoga mat', 24.99, 12.00, 200),
(5, 'BOOK-001', 'Python Programming Book', 'Complete guide to Python programming', 39.99, 20.00, 80);

-- Insert sample customers
INSERT INTO customers (email, password_hash, first_name, last_name, phone, tier) VALUES
('john.doe@example.com', 'hash123', 'John', 'Doe', '+1-555-0101', 'premium'),
('jane.smith@example.com', 'hash456', 'Jane', 'Smith', '+1-555-0102', 'standard'),
('bob.johnson@example.com', 'hash789', 'Bob', 'Johnson', '+1-555-0103', 'premium'),
('alice.williams@example.com', 'hash101', 'Alice', 'Williams', '+1-555-0104', 'standard'),
(NULL, 'hash202', 'Guest', 'User', '+1-555-0105', 'standard'),  -- For null email scenario
('charlie.brown@example.com', 'hash303', 'Charlie', 'Brown', '+1-555-0106', 'premium'),
('diana.prince@example.com', 'hash404', 'Diana', 'Prince', '+1-555-0107', 'standard');

-- Insert sample addresses
INSERT INTO addresses (customer_id, address_type, street_address, city, state, postal_code, is_default) VALUES
(1, 'billing', '123 Main St', 'New York', 'NY', '10001', true),
(1, 'shipping', '123 Main St', 'New York', 'NY', '10001', true),
(2, 'billing', '456 Oak Ave', 'Los Angeles', 'CA', '90001', true),
(2, 'shipping', '456 Oak Ave', 'Los Angeles', 'CA', '90001', true),
(3, 'billing', '789 Pine Rd', 'Chicago', 'IL', '60601', true),
(3, 'shipping', '789 Pine Rd', 'Chicago', 'IL', '60601', true);

-- Insert sample orders
INSERT INTO orders (customer_id, order_number, status, subtotal, tax, shipping, total, billing_address_id, shipping_address_id) VALUES
(1, 'ORD-2024-001', 'completed', 109.98, 8.80, 5.99, 124.77, 1, 1),
(2, 'ORD-2024-002', 'shipped', 69.98, 5.60, 5.99, 81.57, 2, 2),
(3, 'ORD-2024-003', 'pending', 179.97, 14.40, 0.00, 194.37, 3, 3),
(4, 'ORD-2024-004', 'processing', 39.99, 3.20, 5.99, 49.18, NULL, NULL),
(1, 'ORD-2024-005', 'completed', 249.96, 20.00, 0.00, 269.96, 1, 1),
(6, 'ORD-2024-006', 'cancelled', 89.97, 7.20, 5.99, 103.16, NULL, NULL);

-- Insert sample order items
INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_amount) VALUES
(1, 1, 1, 79.99, 0.00),
(1, 2, 2, 14.99, 0.00),
(2, 4, 2, 19.99, 0.00),
(2, 7, 1, 29.99, 0.00),
(3, 1, 2, 79.99, 0.00),
(3, 6, 1, 19.99, 0.00),
(4, 8, 1, 39.99, 0.00),
(5, 1, 3, 79.99, 0.00),
(5, 3, 1, 0.00, 29.99),  -- For zero price scenario (discount)
(6, 5, 1, 49.99, 0.00),
(6, 7, 2, 19.99, 0.00);

-- Insert sample payments
INSERT INTO payments (order_id, payment_method, payment_status, amount, transaction_id) VALUES
(1, 'credit_card', 'completed', 124.77, 'TXN-001'),
(2, 'paypal', 'completed', 81.57, 'TXN-002'),
(3, 'credit_card', 'pending', 194.37, NULL),
(4, 'credit_card', 'pending', 49.18, NULL),
(5, 'credit_card', 'completed', 269.96, 'TXN-003'),
(6, 'credit_card', 'refunded', 103.16, 'TXN-004');

-- Insert sample shipments
INSERT INTO shipments (order_id, tracking_number, carrier, shipping_status, shipped_at) VALUES
(1, 'TRK-123456', 'FedEx', 'delivered', '2024-01-15 10:00:00'),
(2, 'TRK-234567', 'UPS', 'shipped', '2024-01-20 14:30:00'),
(5, 'TRK-345678', 'FedEx', 'delivered', '2024-01-25 09:15:00');

-- Insert sample shipment items
INSERT INTO shipment_items (shipment_id, order_item_id, quantity_shipped) VALUES
(1, 1, 1),
(1, 2, 2),
(2, 3, 2),
(2, 4, 1),
(3, 8, 3),
(3, 9, 1);

-- Insert legacy inventory logs (for orphaned asset scenario)
INSERT INTO legacy_inventory_logs (product_name, old_quantity, new_quantity, reason, logged_by) VALUES
('Old Product A', 100, 50, 'Stock adjustment', 'admin'),
('Old Product B', 200, 0, 'Discontinued', 'admin'),
('Old Product C', 75, 75, 'Manual count', 'warehouse_team');

-- Create indexes for better performance
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);

-- Grant permissions (adjust username as needed)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_username;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_username;

-- Verify data
SELECT 'Categories count:' as info, COUNT(*) as count FROM categories
UNION ALL
SELECT 'Products count:', COUNT(*) FROM products
UNION ALL
SELECT 'Customers count:', COUNT(*) FROM customers
UNION ALL
SELECT 'Addresses count:', COUNT(*) FROM addresses
UNION ALL
SELECT 'Orders count:', COUNT(*) FROM orders
UNION ALL
SELECT 'Order Items count:', COUNT(*) FROM order_items
UNION ALL
SELECT 'Payments count:', COUNT(*) FROM payments
UNION ALL
SELECT 'Shipments count:', COUNT(*) FROM shipments
UNION ALL
SELECT 'Shipment Items count:', COUNT(*) FROM shipment_items
UNION ALL
SELECT 'Legacy Inventory Logs count:', COUNT(*) FROM legacy_inventory_logs;

-- Check for demo scenarios
SELECT 'Null emails (for null spike scenario):' as info, COUNT(*) as count FROM customers WHERE email IS NULL;
SELECT 'Zero unit prices (for quality test scenario):' as info, COUNT(*) as count FROM order_items WHERE unit_price = 0;
SELECT 'Orders without addresses (for orphaned scenario):' as info, COUNT(*) as count FROM orders WHERE billing_address_id IS NULL;
