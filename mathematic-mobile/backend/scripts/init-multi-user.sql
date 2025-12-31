-- ============================================================================
-- Multi-User Database Initialization Script
-- ============================================================================
-- This script creates multiple database users as required for the unified
-- deployment strategy. Each project gets its own user with appropriate
-- permissions.
-- ============================================================================

-- Create ceramic_user if not exists
CREATE USER IF NOT EXISTS 'ceramic_user'@'%' IDENTIFIED BY 'Mysql_2025';
CREATE USER IF NOT EXISTS 'ceramic_user'@'localhost' IDENTIFIED BY 'Mysql_2025';

-- Create stock_user if not exists
CREATE USER IF NOT EXISTS 'stock_user'@'%' IDENTIFIED BY 'Mysql_2025';
CREATE USER IF NOT EXISTS 'stock_user'@'localhost' IDENTIFIED BY 'Mysql_2025';

-- Create mathematic_user if not exists
CREATE USER IF NOT EXISTS 'mathematic_user'@'%' IDENTIFIED BY 'Mysql_2025';
CREATE USER IF NOT EXISTS 'mathematic_user'@'localhost' IDENTIFIED BY 'Mysql_2025';

-- Grant privileges to each user for their respective databases
-- Note: These databases might not exist in this MySQL instance,
-- but we're setting up the users in case of future consolidation

-- Ceramic user privileges (for potential future use)
GRANT ALL PRIVILEGES ON ceramic_db.* TO 'ceramic_user'@'%';
GRANT ALL PRIVILEGES ON ceramic_db.* TO 'ceramic_user'@'localhost';

-- Stock user privileges (for potential future use)
GRANT ALL PRIVILEGES ON stockpredict_db.* TO 'stock_user'@'%';
GRANT ALL PRIVILEGES ON stockpredict_db.* TO 'stock_user'@'localhost';

-- Mathematic user privileges (for the current database)
GRANT ALL PRIVILEGES ON MathematicsSolverDb.* TO 'mathematic_user'@'%';
GRANT ALL PRIVILEGES ON MathematicsSolverDb.* TO 'mathematic_user'@'localhost';
GRANT ALL PRIVILEGES ON mathematic_db.* TO 'mathematic_user'@'%';
GRANT ALL PRIVILEGES ON mathematic_db.* TO 'mathematic_user'@'localhost';

-- Update root password to match our standard
ALTER USER 'root'@'%' IDENTIFIED BY 'Mysql_2025';
ALTER USER 'root'@'localhost' IDENTIFIED BY 'Mysql_2025';

-- Flush privileges to apply changes
FLUSH PRIVILEGES;

-- Display created users
SELECT User, Host FROM mysql.user WHERE User IN ('root', 'ceramic_user', 'stock_user', 'mathematic_user');