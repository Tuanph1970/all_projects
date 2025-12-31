-- Create test users for E2E testing
-- Password for all users: "12345678"
-- Hash: $2b$12$a.WBFT5EjkVGejaQxBhjuuDlAkpF6.X4iMR5rfGevo/Spl2xJGyCG

-- Delete existing test users if they exist
DELETE FROM users WHERE id IN (500, 501, 502);

-- Insert test users
INSERT INTO users (id, email, username, hashed_password, full_name, phone_number, role, is_active, is_verified, created_at)
VALUES
-- test_customer (CUSTOMER role)
(500, 'test_customer@example.com', 'test_customer', '$2b$12$a.WBFT5EjkVGejaQxBhjuuDlAkpF6.X4iMR5rfGevo/Spl2xJGyCG', 'Test Customer', '+1234567500', 'CUSTOMER', 1, 1, NOW()),

-- test_seller (SELLER role)
(501, 'test_seller@example.com', 'test_seller', '$2b$12$a.WBFT5EjkVGejaQxBhjuuDlAkpF6.X4iMR5rfGevo/Spl2xJGyCG', 'Test Seller', '+1234567501', 'SELLER', 1, 1, NOW()),

-- test_dual (DUAL role - can switch between customer and seller)
(502, 'test_dual@example.com', 'test_dual', '$2b$12$a.WBFT5EjkVGejaQxBhjuuDlAkpF6.X4iMR5rfGevo/Spl2xJGyCG', 'Test Dual', '+1234567502', 'DUAL', 1, 1, NOW());

-- Verify inserted users
SELECT id, username, email, role FROM users WHERE id IN (500, 501, 502);
