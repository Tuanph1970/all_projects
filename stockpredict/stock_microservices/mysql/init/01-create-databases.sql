-- MySQL Initialization Script for Stock Helper Microservices
-- Creates separate databases for each service (Database per Service pattern)

-- =============================================================================
-- CREATE DATABASES
-- =============================================================================

-- Auth Service Database
CREATE DATABASE IF NOT EXISTS auth_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Stock Data Service Database
CREATE DATABASE IF NOT EXISTS stockdata_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Portfolio Service Database
CREATE DATABASE IF NOT EXISTS portfolio_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Prediction Service Database
CREATE DATABASE IF NOT EXISTS prediction_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Analysis Service Database
CREATE DATABASE IF NOT EXISTS analysis_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- News Service Database (company + macro news corpus)
CREATE DATABASE IF NOT EXISTS stock_news
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Event-Reaction Service Database (discrete-event store)
CREATE DATABASE IF NOT EXISTS stock_event_reaction
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Legacy Database (for Django monolith during transition)
CREATE DATABASE IF NOT EXISTS defaultdb
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- =============================================================================
-- CREATE USER AND GRANT PERMISSIONS
-- =============================================================================

-- Create service user if not exists
CREATE USER IF NOT EXISTS 'stockuser'@'%' IDENTIFIED BY 'stockpass';

-- Grant permissions on all databases
GRANT ALL PRIVILEGES ON auth_db.* TO 'stockuser'@'%';
GRANT ALL PRIVILEGES ON stockdata_db.* TO 'stockuser'@'%';
GRANT ALL PRIVILEGES ON portfolio_db.* TO 'stockuser'@'%';
GRANT ALL PRIVILEGES ON prediction_db.* TO 'stockuser'@'%';
GRANT ALL PRIVILEGES ON analysis_db.* TO 'stockuser'@'%';
GRANT ALL PRIVILEGES ON stock_news.* TO 'stockuser'@'%';
GRANT ALL PRIVILEGES ON stock_event_reaction.* TO 'stockuser'@'%';
GRANT ALL PRIVILEGES ON defaultdb.* TO 'stockuser'@'%';

FLUSH PRIVILEGES;

-- =============================================================================
-- AUTH_DB TABLES
-- =============================================================================

USE auth_db;

CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NULL,
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    INDEX idx_email (email),
    INDEX idx_username (username)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_user_role (user_id, role)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    token VARCHAR(500) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_token (token(255)),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB;

-- =============================================================================
-- PORTFOLIO_DB TABLES
-- =============================================================================

USE portfolio_db;

CREATE TABLE IF NOT EXISTS portfolios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    name VARCHAR(100) DEFAULT 'Default Portfolio',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    quantity DECIMAL(18, 4) NOT NULL,
    average_price DECIMAL(18, 4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    UNIQUE KEY unique_portfolio_ticker (portfolio_id, ticker),
    INDEX idx_ticker (ticker)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS transactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    portfolio_id INT NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    transaction_type ENUM('BUY', 'SELL') NOT NULL,
    quantity DECIMAL(18, 4) NOT NULL,
    price DECIMAL(18, 4) NOT NULL,
    total_value DECIMAL(18, 4) NOT NULL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE,
    INDEX idx_portfolio_id (portfolio_id),
    INDEX idx_ticker (ticker),
    INDEX idx_transaction_date (transaction_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS price_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    ticker VARCHAR(20) NOT NULL,
    alert_type ENUM('ABOVE', 'BELOW', 'CHANGE_PERCENT') NOT NULL,
    target_value DECIMAL(18, 4) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    triggered_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_ticker (ticker),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB;

-- =============================================================================
-- LOG COMPLETION
-- =============================================================================

SELECT 'Database initialization completed successfully!' AS status;
