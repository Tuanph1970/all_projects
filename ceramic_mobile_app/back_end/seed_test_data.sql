-- Ceramic Marketplace Test Data Seed Script
-- This script creates fake data for testing purposes
-- Run this script before running test suites

USE ceramic_marketplace;

-- Disable foreign key checks temporarily
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- SECTION 1: Create Test Users
-- ============================================

-- Create test customers (IDs: 100-104)
-- Password for all test users: Mysql_2025!
REPLACE INTO users (id, email, username, hashed_password, full_name, phone_number, role, is_active, is_verified, created_at)
VALUES
(100, 'customer_a@test.com', 'customer_a', '$2b$12$UusiPB9I4cBUfcY3qmlk2.BtGOv.mCGCXXfLKfkXqyN.Ol/6DuZ5m', 'Customer A', '+1234567001', 'CUSTOMER', 1, 1, NOW()),
(101, 'customer_b@test.com', 'customer_b', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Customer B', '+1234567002', 'CUSTOMER', 1, 1, NOW()),
(102, 'customer_c@test.com', 'customer_c', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Customer C', '+1234567003', 'CUSTOMER', 1, 1, NOW()),
(103, 'customer_d@test.com', 'customer_d', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Customer D', '+1234567004', 'CUSTOMER', 1, 1, NOW()),
(104, 'customer_e@test.com', 'customer_e', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Customer E', '+1234567005', 'CUSTOMER', 1, 1, NOW());

-- Create test sellers (IDs: 200-204)
-- Password for all test users: Mysql_2025!
REPLACE INTO users (id, email, username, hashed_password, full_name, phone_number, role, is_active, is_verified, shop_name, shop_description, created_at)
VALUES
(200, 'seller_a@test.com', 'seller_a', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Seller A', '+1234567201', 'SELLER', 1, 1, 'Ceramics Shop A', 'Premium handcrafted ceramics', NOW()),
(201, 'seller_b@test.com', 'seller_b', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Seller B', '+1234567202', 'SELLER', 1, 1, 'Ceramics Shop B', 'Traditional pottery and ceramics', NOW()),
(202, 'seller_c@test.com', 'seller_c', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Seller C', '+1234567203', 'SELLER', 1, 1, 'Ceramics Shop C', 'Modern ceramic designs', NOW()),
(203, 'seller_d@test.com', 'seller_d', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Seller D', '+1234567204', 'SELLER', 1, 1, 'Ceramics Shop D', 'Artisan ceramics and tiles', NOW()),
(204, 'seller_e@test.com', 'seller_e', '$2b$12$W7zFfg4Gq53hRECfjo.6Huk4DLUdS0e6/bdafiG.WKDzd1f9Z7hYK', 'Seller E', '+1234567205', 'SELLER', 1, 1, 'Ceramics Shop E', 'Contemporary ceramic art', NOW());

-- ============================================
-- SECTION 2: Create Categories
-- ============================================

INSERT IGNORE INTO categories (id, name, description, is_active, created_at)
VALUES
(100, 'Tableware', 'Plates, bowls, cups, and dining essentials', 1, NOW()),
(101, 'Decorative Items', 'Vases, sculptures, and ornamental pieces', 1, NOW()),
(102, 'Tiles', 'Floor and wall tiles', 1, NOW()),
(103, 'Kitchenware', 'Ceramic cookware and kitchen tools', 1, NOW()),
(104, 'Art Pieces', 'Handcrafted ceramic artworks', 1, NOW());

-- ============================================
-- SECTION 3: Create Products
-- ============================================

-- Products from Seller A (IDs: 1000-1009)
INSERT IGNORE INTO products (id, name, description, price, quantity_available, material, color, seller_id, category_id, is_active, is_featured, sku, created_at)
VALUES
(1000, 'product_A1', 'Handcrafted ceramic dinner plate', 29.99, 50, 'Porcelain', 'White', 200, 100, 1, 1, 'PROD-A1-001', NOW()),
(1001, 'product_A2', 'Decorative ceramic vase', 49.99, 30, 'Stoneware', 'Blue', 200, 101, 1, 1, 'PROD-A2-002', NOW()),
(1002, 'product_A3', 'Ceramic coffee mug set', 39.99, 40, 'Ceramic', 'Mixed', 200, 100, 1, 0, 'PROD-A3-003', NOW()),
(1003, 'product_A4', 'Kitchen tile set', 89.99, 20, 'Ceramic', 'Beige', 200, 102, 1, 0, 'PROD-A4-004', NOW()),
(1004, 'product_A5', 'Ceramic fruit bowl', 34.99, 35, 'Stoneware', 'Green', 200, 103, 1, 1, 'PROD-A5-005', NOW());

-- Products from Seller B (IDs: 1010-1019)
INSERT IGNORE INTO products (id, name, description, price, quantity_available, material, color, seller_id, category_id, is_active, is_featured, sku, created_at)
VALUES
(1010, 'product_B1', 'Traditional tea set', 79.99, 25, 'Porcelain', 'White', 201, 100, 1, 1, 'PROD-B1-010', NOW()),
(1011, 'product_B2', 'Ceramic sculpture', 149.99, 10, 'Ceramic', 'Natural', 201, 104, 1, 1, 'PROD-B2-011', NOW()),
(1012, 'product_B3', 'Decorative plate set', 59.99, 45, 'Porcelain', 'Blue', 201, 100, 1, 0, 'PROD-B3-012', NOW()),
(1013, 'product_B4', 'Ceramic planter', 24.99, 60, 'Terracotta', 'Red', 201, 101, 1, 0, 'PROD-B4-013', NOW()),
(1014, 'product_B5', 'Wall tile collection', 99.99, 15, 'Ceramic', 'Grey', 201, 102, 1, 1, 'PROD-B5-014', NOW());

-- Products from Seller C (IDs: 1020-1029)
INSERT IGNORE INTO products (id, name, description, price, quantity_available, material, color, seller_id, category_id, is_active, is_featured, sku, created_at)
VALUES
(1020, 'product_C1', 'Modern ceramic bowl', 44.99, 55, 'Stoneware', 'Black', 202, 100, 1, 1, 'PROD-C1-020', NOW()),
(1021, 'product_C2', 'Abstract ceramic art', 199.99, 8, 'Ceramic', 'Multicolor', 202, 104, 1, 1, 'PROD-C2-021', NOW()),
(1022, 'product_C3', 'Espresso cup set', 49.99, 40, 'Porcelain', 'White', 202, 100, 1, 0, 'PROD-C3-022', NOW()),
(1023, 'product_C4', 'Ceramic serving dish', 54.99, 30, 'Stoneware', 'Blue', 202, 103, 1, 0, 'PROD-C4-023', NOW()),
(1024, 'product_C5', 'Decorative ceramic jar', 39.99, 38, 'Ceramic', 'Yellow', 202, 101, 1, 1, 'PROD-C5-024', NOW());

-- Products from Seller D (IDs: 1030-1039)
INSERT IGNORE INTO products (id, name, description, price, quantity_available, material, color, seller_id, category_id, is_active, is_featured, sku, created_at)
VALUES
(1030, 'product_D1', 'Floor tile premium', 129.99, 50, 'Ceramic', 'Brown', 203, 102, 1, 1, 'PROD-D1-030', NOW()),
(1031, 'product_D2', 'Ceramic dinner set', 189.99, 12, 'Porcelain', 'White', 203, 100, 1, 1, 'PROD-D2-031', NOW()),
(1032, 'product_D3', 'Artisan vase collection', 79.99, 22, 'Stoneware', 'Mixed', 203, 101, 1, 0, 'PROD-D3-032', NOW()),
(1033, 'product_D4', 'Ceramic baking dish', 44.99, 42, 'Ceramic', 'Red', 203, 103, 1, 0, 'PROD-D4-033', NOW()),
(1034, 'product_D5', 'Mosaic tile set', 159.99, 18, 'Ceramic', 'Multicolor', 203, 102, 1, 1, 'PROD-D5-034', NOW());

-- Products from Seller E (IDs: 1040-1049)
INSERT IGNORE INTO products (id, name, description, price, quantity_available, material, color, seller_id, category_id, is_active, is_featured, sku, created_at)
VALUES
(1040, 'product_E1', 'Contemporary plate set', 69.99, 35, 'Porcelain', 'Grey', 204, 100, 1, 1, 'PROD-E1-040', NOW()),
(1041, 'product_E2', 'Ceramic art sculpture', 249.99, 5, 'Ceramic', 'Natural', 204, 104, 1, 1, 'PROD-E2-041', NOW()),
(1042, 'product_E3', 'Decorative bowl set', 54.99, 48, 'Stoneware', 'Blue', 204, 101, 1, 0, 'PROD-E3-042', NOW()),
(1043, 'product_E4', 'Ceramic canister set', 39.99, 52, 'Ceramic', 'White', 204, 103, 1, 0, 'PROD-E4-043', NOW()),
(1044, 'product_E5', 'Designer tile collection', 179.99, 14, 'Ceramic', 'Black', 204, 102, 1, 1, 'PROD-E5-044', NOW());

-- Products for Customer A (who is also a seller - for testing image management)
INSERT IGNORE INTO products (id, name, description, price, quantity_available, material, color, seller_id, category_id, is_active, is_featured, sku, created_at)
VALUES
(1050, 'product_TEST1', 'Test ceramic bowl for image management', 45.99, 20, 'Ceramic', 'White', 100, 100, 1, 0, 'PROD-TEST-050', NOW()),
(1051, 'product_TEST2', 'Test vase for bulk operations', 55.99, 15, 'Stoneware', 'Blue', 100, 101, 1, 0, 'PROD-TEST-051', NOW()),
(1052, 'product_TEST3', 'Test plate for bulk operations', 35.99, 25, 'Porcelain', 'Grey', 100, 100, 1, 0, 'PROD-TEST-052', NOW());

-- ============================================
-- SECTION 4: Create Product Images
-- ============================================

-- Add sample images for featured products and commonly tested products
INSERT IGNORE INTO product_images (product_id, image_url, alt_text, is_primary, order_index, created_at)
VALUES
-- Images for product 1000 (has reviews, tested product)
(1000, 'https://example.com/images/product_A1_main.jpg', 'Handcrafted ceramic dinner plate - main view', 1, 0, NOW()),
(1000, 'https://example.com/images/product_A1_detail.jpg', 'Handcrafted ceramic dinner plate - detail', 0, 1, NOW()),

-- Images for product 1001 (used in Add to Cart test)
(1001, 'https://example.com/images/product_A2_main.jpg', 'Decorative ceramic vase - main view', 1, 0, NOW()),
(1001, 'https://example.com/images/product_A2_side.jpg', 'Decorative ceramic vase - side view', 0, 1, NOW()),
(1001, 'https://example.com/images/product_A2_top.jpg', 'Decorative ceramic vase - top view', 0, 2, NOW()),

-- Images for product 1002 (in cart items)
(1002, 'https://example.com/images/product_A3_main.jpg', 'Ceramic coffee mug set - main view', 1, 0, NOW()),
(1002, 'https://example.com/images/product_A3_detail.jpg', 'Ceramic coffee mug set - detail', 0, 1, NOW()),

-- Images for featured products
(1004, 'https://example.com/images/product_A5_main.jpg', 'Ceramic fruit bowl - main view', 1, 0, NOW()),
(1010, 'https://example.com/images/product_B1_main.jpg', 'Traditional tea set - main view', 1, 0, NOW()),
(1011, 'https://example.com/images/product_B2_main.jpg', 'Ceramic sculpture - main view', 1, 0, NOW()),
(1014, 'https://example.com/images/product_B5_main.jpg', 'Wall tile collection - main view', 1, 0, NOW()),
(1020, 'https://example.com/images/product_C1_main.jpg', 'Modern ceramic bowl - main view', 1, 0, NOW()),
(1021, 'https://example.com/images/product_C2_main.jpg', 'Abstract ceramic art - main view', 1, 0, NOW()),
(1024, 'https://example.com/images/product_C5_main.jpg', 'Decorative ceramic jar - main view', 1, 0, NOW()),

-- Images for reviewed products
(1022, 'https://example.com/images/product_C3_main.jpg', 'Espresso cup set - main view', 1, 0, NOW()),
(1030, 'https://example.com/images/product_D1_main.jpg', 'Floor tile premium - main view', 1, 0, NOW()),
(1031, 'https://example.com/images/product_D2_main.jpg', 'Ceramic dinner set - main view', 1, 0, NOW()),
(1034, 'https://example.com/images/product_D5_main.jpg', 'Mosaic tile set - main view', 1, 0, NOW()),
(1040, 'https://example.com/images/product_E1_main.jpg', 'Contemporary plate set - main view', 1, 0, NOW()),
(1041, 'https://example.com/images/product_E2_main.jpg', 'Ceramic art sculpture - main view', 1, 0, NOW()),
(1042, 'https://example.com/images/product_E3_main.jpg', 'Decorative bowl set - main view', 1, 0, NOW()),
(1044, 'https://example.com/images/product_E5_main.jpg', 'Designer tile collection - main view', 1, 0, NOW()),

-- Images for test products owned by Customer A (for image management tests)
(1050, 'https://example.com/images/product_TEST1_main.jpg', 'Test ceramic bowl - main view', 1, 0, NOW()),
(1050, 'https://example.com/images/product_TEST1_side.jpg', 'Test ceramic bowl - side view', 0, 1, NOW()),
(1050, 'https://example.com/images/product_TEST1_top.jpg', 'Test ceramic bowl - top view', 0, 2, NOW());

-- ============================================
-- SECTION 5: Create Orders
-- ============================================

-- Orders for testing (IDs: 2000-2019)
-- Order 2000: Customer A buys from Seller A - DELIVERED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at, updated_at, shipped_at, delivered_at)
VALUES
(2000, 'ORDER-2000', 100, 200, 'DELIVERED', 'COMPLETED', 29.99, 2.40, 5.99, 38.38,
 '123 Main St', 'New York', 'NY', '10001', 'USA', NOW() - INTERVAL 30 DAY, NOW() - INTERVAL 25 DAY, NOW() - INTERVAL 28 DAY, NOW() - INTERVAL 25 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2000, 1000, 1, 29.99, 29.99, 'product_A1', 'Handcrafted ceramic dinner plate', NOW() - INTERVAL 30 DAY);

-- Order 2001: Customer A buys from Seller B - SHIPPED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, tracking_number, shipping_carrier, created_at, updated_at, shipped_at)
VALUES
(2001, 'ORDER-2001', 100, 201, 'SHIPPED', 'COMPLETED', 79.99, 6.40, 7.99, 94.38,
 '123 Main St', 'New York', 'NY', '10001', 'USA', 'TRK123456', 'FedEx', NOW() - INTERVAL 5 DAY, NOW() - INTERVAL 3 DAY, NOW() - INTERVAL 3 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2001, 1010, 1, 79.99, 79.99, 'product_B1', 'Traditional tea set', NOW() - INTERVAL 5 DAY);

-- Order 2002: Customer B buys from Seller A - PROCESSING
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at, updated_at)
VALUES
(2002, 'ORDER-2002', 101, 200, 'PROCESSING', 'COMPLETED', 89.98, 7.20, 6.99, 104.17,
 '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'USA', NOW() - INTERVAL 3 DAY, NOW() - INTERVAL 2 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2002, 1001, 1, 49.99, 49.99, 'product_A2', 'Decorative ceramic vase', NOW() - INTERVAL 3 DAY),
(2002, 1002, 1, 39.99, 39.99, 'product_A3', 'Ceramic coffee mug set', NOW() - INTERVAL 3 DAY);

-- Order 2003: Customer B buys from Seller C - CONFIRMED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at, updated_at)
VALUES
(2003, 'ORDER-2003', 101, 202, 'CONFIRMED', 'COMPLETED', 44.99, 3.60, 5.99, 54.58,
 '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'USA', NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 1 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2003, 1020, 1, 44.99, 44.99, 'product_C1', 'Modern ceramic bowl', NOW() - INTERVAL 2 DAY);

-- Order 2004: Customer C buys from Seller D - PENDING
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at)
VALUES
(2004, 'ORDER-2004', 102, 203, 'PENDING', 'PENDING', 129.99, 10.40, 9.99, 150.38,
 '789 Pine Rd', 'Chicago', 'IL', '60601', 'USA', NOW() - INTERVAL 1 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2004, 1030, 1, 129.99, 129.99, 'product_D1', 'Floor tile premium', NOW() - INTERVAL 1 DAY);

-- Order 2005: Customer C buys from Seller E - DELIVERED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at, updated_at, shipped_at, delivered_at)
VALUES
(2005, 'ORDER-2005', 102, 204, 'DELIVERED', 'COMPLETED', 69.99, 5.60, 6.99, 82.58,
 '789 Pine Rd', 'Chicago', 'IL', '60601', 'USA', NOW() - INTERVAL 20 DAY, NOW() - INTERVAL 15 DAY, NOW() - INTERVAL 18 DAY, NOW() - INTERVAL 15 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2005, 1040, 1, 69.99, 69.99, 'product_E1', 'Contemporary plate set', NOW() - INTERVAL 20 DAY);

-- Order 2006: Customer D buys multiple items from Seller A - SHIPPED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, tracking_number, shipping_carrier, created_at, updated_at, shipped_at)
VALUES
(2006, 'ORDER-2006', 103, 200, 'SHIPPED', 'COMPLETED', 154.96, 12.40, 8.99, 176.35,
 '321 Elm St', 'Houston', 'TX', '77001', 'USA', 'TRK789012', 'UPS', NOW() - INTERVAL 7 DAY, NOW() - INTERVAL 5 DAY, NOW() - INTERVAL 5 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2006, 1000, 2, 29.99, 59.98, 'product_A1', 'Handcrafted ceramic dinner plate', NOW() - INTERVAL 7 DAY),
(2006, 1004, 1, 34.99, 34.99, 'product_A5', 'Ceramic fruit bowl', NOW() - INTERVAL 7 DAY),
(2006, 1003, 1, 89.99, 89.99, 'product_A4', 'Kitchen tile set', NOW() - INTERVAL 7 DAY);

-- Order 2007: Customer D buys from Seller B - PROCESSING
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at, updated_at)
VALUES
(2007, 'ORDER-2007', 103, 201, 'PROCESSING', 'COMPLETED', 84.98, 6.80, 7.99, 99.77,
 '321 Elm St', 'Houston', 'TX', '77001', 'USA', NOW() - INTERVAL 4 DAY, NOW() - INTERVAL 3 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2007, 1012, 1, 59.99, 59.99, 'product_B3', 'Decorative plate set', NOW() - INTERVAL 4 DAY),
(2007, 1013, 1, 24.99, 24.99, 'product_B4', 'Ceramic planter', NOW() - INTERVAL 4 DAY);

-- Order 2008: Customer E buys from Seller C - DELIVERED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at, updated_at, shipped_at, delivered_at)
VALUES
(2008, 'ORDER-2008', 104, 202, 'DELIVERED', 'COMPLETED', 104.98, 8.40, 7.99, 121.37,
 '654 Maple Dr', 'Phoenix', 'AZ', '85001', 'USA', NOW() - INTERVAL 15 DAY, NOW() - INTERVAL 10 DAY, NOW() - INTERVAL 13 DAY, NOW() - INTERVAL 10 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2008, 1022, 1, 49.99, 49.99, 'product_C3', 'Espresso cup set', NOW() - INTERVAL 15 DAY),
(2008, 1023, 1, 54.99, 54.99, 'product_C4', 'Ceramic serving dish', NOW() - INTERVAL 15 DAY);

-- Order 2009: Customer E buys from Seller D - CONFIRMED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at)
VALUES
(2009, 'ORDER-2009', 104, 203, 'CONFIRMED', 'COMPLETED', 189.99, 15.20, 9.99, 215.18,
 '654 Maple Dr', 'Phoenix', 'AZ', '85001', 'USA', NOW() - INTERVAL 2 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2009, 1031, 1, 189.99, 189.99, 'product_D2', 'Ceramic dinner set', NOW() - INTERVAL 2 DAY);

-- Order 2010: Customer A buys from Seller E - CANCELLED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at, updated_at)
VALUES
(2010, 'ORDER-2010', 100, 204, 'CANCELLED', 'REFUNDED', 54.99, 4.40, 6.99, 66.38,
 '123 Main St', 'New York', 'NY', '10001', 'USA', NOW() - INTERVAL 8 DAY, NOW() - INTERVAL 7 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2010, 1042, 1, 54.99, 54.99, 'product_E3', 'Decorative bowl set', NOW() - INTERVAL 8 DAY);

-- Order 2013: Customer A buys product for review testing - DELIVERED
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at, updated_at, shipped_at, delivered_at)
VALUES
(2013, 'ORDER-2013', 100, 200, 'DELIVERED', 'COMPLETED', 49.99, 4.00, 5.99, 59.98,
 '123 Main St', 'New York', 'NY', '10001', 'USA', NOW() - INTERVAL 5 DAY, NOW() - INTERVAL 2 DAY, NOW() - INTERVAL 4 DAY, NOW() - INTERVAL 2 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2013, 1002, 1, 49.99, 49.99, 'product_A3', 'Ceramic coffee mug set', NOW() - INTERVAL 5 DAY);

-- Order 2100: Customer B buys from Customer A (who is also a seller) - PENDING
INSERT IGNORE INTO orders (id, order_number, customer_id, seller_id, status, payment_status, subtotal, tax_amount, shipping_amount, total_amount,
                    shipping_address_line1, shipping_city, shipping_state, shipping_postal_code, shipping_country, created_at)
VALUES
(2100, 'ORDER-2100', 101, 100, 'PENDING', 'PENDING', 45.99, 3.68, 5.99, 55.66,
 '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'USA', NOW() - INTERVAL 1 DAY);

INSERT IGNORE INTO order_items (order_id, product_id, quantity, unit_price, total_price, product_name, product_description, created_at)
VALUES
(2100, 1050, 1, 45.99, 45.99, 'product_TEST1', 'Test ceramic bowl for image management', NOW() - INTERVAL 1 DAY);

-- ============================================
-- SECTION 6: Create Reviews
-- ============================================

-- Reviews for products (sample reviews linked to orders)
INSERT IGNORE INTO reviews (product_id, reviewer_id, seller_id, order_id, rating, title, comment, is_verified_purchase, is_approved, created_at)
VALUES
(1000, 100, 200, 2000, 5, 'Excellent quality!', 'Beautiful plate, exactly as described. Very satisfied!', 1, 1, NOW() - INTERVAL 25 DAY),
(1010, 100, 201, 2001, 4, 'Great tea set', 'Good quality, but shipping took longer than expected.', 1, 1, NOW() - INTERVAL 3 DAY),
(1020, 101, 202, 2003, 5, 'Perfect modern design', 'Love the minimalist style of this bowl!', 1, 1, NOW() - INTERVAL 1 DAY),
(1030, 102, 203, 2004, 5, 'Premium tiles', 'High quality tiles, perfect for my kitchen renovation.', 0, 1, NOW() - INTERVAL 1 DAY),
(1040, 102, 204, 2005, 5, 'Beautiful plates', 'Contemporary design, perfect for dinner parties.', 1, 1, NOW() - INTERVAL 15 DAY),
(1000, 103, 200, 2006, 4, 'Good value', 'Nice plates for the price, minor imperfections but acceptable.', 1, 1, NOW() - INTERVAL 5 DAY),
(1022, 104, 202, 2008, 5, 'Love these cups!', 'Perfect size for espresso, stylish design.', 1, 1, NOW() - INTERVAL 10 DAY),
(1031, 104, 203, 2009, 5, 'Complete dinner set', 'Gorgeous set, excellent craftsmanship.', 1, 1, NOW() - INTERVAL 2 DAY);

-- ============================================
-- SECTION 7: Create Shipping Addresses
-- ============================================

INSERT IGNORE INTO shipping_addresses (user_id, title, full_name, phone_number, address_line1, city, state, postal_code, country, is_default, is_active, created_at)
VALUES
(100, 'Home', 'Customer A', '+1234567001', '123 Main St', 'New York', 'NY', '10001', 'USA', 1, 1, NOW()),
(101, 'Home', 'Customer B', '+1234567002', '456 Oak Ave', 'Los Angeles', 'CA', '90001', 'USA', 1, 1, NOW()),
(102, 'Home', 'Customer C', '+1234567003', '789 Pine Rd', 'Chicago', 'IL', '60601', 'USA', 1, 1, NOW()),
(103, 'Home', 'Customer D', '+1234567004', '321 Elm St', 'Houston', 'TX', '77001', 'USA', 1, 1, NOW()),
(104, 'Home', 'Customer E', '+1234567005', '654 Maple Dr', 'Phoenix', 'AZ', '85001', 'USA', 1, 1, NOW());

-- ============================================
-- SECTION 8: Create Carts
-- ============================================

-- Create carts for test customers
INSERT IGNORE INTO carts (user_id, created_at, updated_at)
VALUES
(100, NOW(), NOW()),
(101, NOW(), NOW()),
(102, NOW(), NOW()),
(103, NOW(), NOW()),
(104, NOW(), NOW());

-- Clear existing cart items first to ensure fresh data
DELETE FROM cart_items WHERE cart_id IN (SELECT id FROM carts WHERE user_id IN (100, 101, 102, 103, 104));

-- Add some cart items for Customer A (with explicit IDs for testing)
INSERT INTO cart_items (id, cart_id, product_id, quantity, unit_price, total_price, created_at, updated_at)
SELECT 1, c.id, 1001, 1, 49.99, 49.99, NOW(), NOW()
FROM carts c WHERE c.user_id = 100
ON DUPLICATE KEY UPDATE quantity=1, unit_price=49.99, total_price=49.99, updated_at=NOW();

INSERT INTO cart_items (id, cart_id, product_id, quantity, unit_price, total_price, created_at, updated_at)
SELECT 2, c.id, 1002, 2, 39.99, 79.98, NOW(), NOW()
FROM carts c WHERE c.user_id = 100
ON DUPLICATE KEY UPDATE quantity=2, unit_price=39.99, total_price=79.98, updated_at=NOW();

-- Add cart items for Customer B
INSERT INTO cart_items (id, cart_id, product_id, quantity, unit_price, total_price, created_at, updated_at)
SELECT 3, c.id, 1020, 1, 44.99, 44.99, NOW(), NOW()
FROM carts c WHERE c.user_id = 101
ON DUPLICATE KEY UPDATE quantity=1, unit_price=44.99, total_price=44.99, updated_at=NOW();

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Verify data insertion
SELECT 'Users created:' AS Info, COUNT(*) AS Count FROM users WHERE id >= 100 AND id <= 204;
SELECT 'Categories created:' AS Info, COUNT(*) AS Count FROM categories WHERE id >= 100 AND id <= 104;
SELECT 'Products created:' AS Info, COUNT(*) AS Count FROM products WHERE id >= 1000 AND id <= 1044;
SELECT 'Product images created:' AS Info, COUNT(*) AS Count FROM product_images WHERE product_id >= 1000 AND product_id <= 1044;
SELECT 'Orders created:' AS Info, COUNT(*) AS Count FROM orders WHERE id >= 2000 AND id <= 2010;
SELECT 'Order items created:' AS Info, COUNT(*) AS Count FROM order_items WHERE order_id >= 2000 AND order_id <= 2010;
SELECT 'Reviews created:' AS Info, COUNT(*) AS Count FROM reviews WHERE product_id >= 1000;
SELECT 'Shipping addresses created:' AS Info, COUNT(*) AS Count FROM shipping_addresses WHERE user_id >= 100 AND user_id <= 104;
SELECT 'Carts created:' AS Info, COUNT(*) AS Count FROM carts WHERE user_id >= 100 AND user_id <= 104;
SELECT 'Cart items created:' AS Info, COUNT(*) AS Count FROM cart_items WHERE cart_id IN (SELECT id FROM carts WHERE user_id >= 100 AND user_id <= 104);

-- Summary
SELECT '=================================================' AS ' ';
SELECT 'TEST DATA SEED COMPLETED SUCCESSFULLY!' AS Status;
SELECT '=================================================' AS ' ';
SELECT 'Test Users: 10 (5 customers + 5 sellers)' AS Summary;
SELECT 'Test Categories: 5' AS Summary;
SELECT 'Test Products: 25 (5 per seller)' AS Summary;
SELECT 'Test Product Images: 22 (for featured and tested products)' AS Summary;
SELECT 'Test Orders: 11 (various statuses)' AS Summary;
SELECT 'Test Reviews: 8' AS Summary;
SELECT '=================================================' AS ' ';
