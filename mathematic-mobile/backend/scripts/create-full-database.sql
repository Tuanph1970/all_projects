-- ============================================
-- Mathematics Solver Database - Complete Schema
-- ============================================
-- This script creates the complete database structure including:
-- - Database creation
-- - All tables with proper data types
-- - Indexes for performance
-- - Foreign key relationships
-- - Constraints and defaults
-- ============================================

-- Create Database
CREATE DATABASE IF NOT EXISTS MathematicsSolverDb
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE MathematicsSolverDb;

-- ============================================
-- Table: Users
-- ============================================
CREATE TABLE IF NOT EXISTS Users (
    Id CHAR(36) PRIMARY KEY,
    Username VARCHAR(50) NOT NULL,
    Email VARCHAR(100) NOT NULL,
    PasswordHash VARCHAR(255) NOT NULL,
    IsActive TINYINT(1) NOT NULL DEFAULT 1,
    CreatedAt DATETIME(6) NOT NULL,
    UpdatedAt DATETIME(6) NULL,
    LastLoginAt DATETIME(6) NULL,

    -- Unique Constraints
    CONSTRAINT UQ_Users_Username UNIQUE (Username),
    CONSTRAINT UQ_Users_Email UNIQUE (Email),

    -- Check Constraints
    CONSTRAINT CK_Users_Username_Length CHECK (CHAR_LENGTH(Username) >= 3),
    CONSTRAINT CK_Users_Email_Format CHECK (Email LIKE '%@%.%')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indexes for Users
CREATE INDEX IX_Users_Username ON Users(Username);
CREATE INDEX IX_Users_Email ON Users(Email);
CREATE INDEX IX_Users_IsActive ON Users(IsActive);
CREATE INDEX IX_Users_CreatedAt ON Users(CreatedAt);

-- ============================================
-- Table: Problems
-- ============================================
CREATE TABLE IF NOT EXISTS Problems (
    Id CHAR(36) PRIMARY KEY,
    UserId CHAR(36) NOT NULL,
    ImageUrl VARCHAR(500) NOT NULL,
    Category VARCHAR(100) NOT NULL,
    Status INT NOT NULL DEFAULT 0,
    Description VARCHAR(1000) NULL,
    CreatedAt DATETIME(6) NOT NULL,
    UpdatedAt DATETIME(6) NULL,

    -- Foreign Key
    CONSTRAINT FK_Problems_Users_UserId
        FOREIGN KEY (UserId)
        REFERENCES Users(Id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- Check Constraints
    CONSTRAINT CK_Problems_Status CHECK (Status IN (0, 1, 2, 3)),
    CONSTRAINT CK_Problems_ImageUrl_Length CHECK (CHAR_LENGTH(ImageUrl) > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indexes for Problems
CREATE INDEX IX_Problems_UserId ON Problems(UserId);
CREATE INDEX IX_Problems_Status ON Problems(Status);
CREATE INDEX IX_Problems_Category ON Problems(Category);
CREATE INDEX IX_Problems_CreatedAt ON Problems(CreatedAt);
CREATE INDEX IX_Problems_Status_Category ON Problems(Status, Category);

-- ============================================
-- Table: Solutions
-- ============================================
CREATE TABLE IF NOT EXISTS Solutions (
    Id CHAR(36) PRIMARY KEY,
    ProblemId CHAR(36) NOT NULL,
    Steps JSON NOT NULL,
    Confidence DECIMAL(5,4) NOT NULL,
    AdditionalNotes VARCHAR(2000) NULL,
    CreatedAt DATETIME(6) NOT NULL,
    UpdatedAt DATETIME(6) NULL,

    -- Foreign Key
    CONSTRAINT FK_Solutions_Problems_ProblemId
        FOREIGN KEY (ProblemId)
        REFERENCES Problems(Id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    -- Unique Constraint (One solution per problem)
    CONSTRAINT UQ_Solutions_ProblemId UNIQUE (ProblemId),

    -- Check Constraints
    CONSTRAINT CK_Solutions_Confidence CHECK (Confidence >= 0.0000 AND Confidence <= 1.0000)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Indexes for Solutions
CREATE UNIQUE INDEX IX_Solutions_ProblemId ON Solutions(ProblemId);
CREATE INDEX IX_Solutions_Confidence ON Solutions(Confidence);
CREATE INDEX IX_Solutions_CreatedAt ON Solutions(CreatedAt);

-- ============================================
-- Insert Sample Data (Optional - for testing)
-- ============================================

-- Uncomment the following lines to add sample data

-- INSERT INTO Users (Id, Username, Email, PasswordHash, IsActive, CreatedAt)
-- VALUES
--     (UUID(), 'testuser', 'test@example.com', '$2a$11$hashed_password_here', 1, NOW(6)),
--     (UUID(), 'demouser', 'demo@example.com', '$2a$11$another_hashed_password', 1, NOW(6));

-- ============================================
-- Useful Queries
-- ============================================

-- View all tables
-- SHOW TABLES;

-- View table structure
-- DESCRIBE Users;
-- DESCRIBE Problems;
-- DESCRIBE Solutions;

-- View indexes
-- SHOW INDEX FROM Users;
-- SHOW INDEX FROM Problems;
-- SHOW INDEX FROM Solutions;

-- View foreign key relationships
-- SELECT
--     CONSTRAINT_NAME,
--     TABLE_NAME,
--     REFERENCED_TABLE_NAME
-- FROM information_schema.KEY_COLUMN_USAGE
-- WHERE TABLE_SCHEMA = 'MathematicsSolverDb'
--     AND REFERENCED_TABLE_NAME IS NOT NULL;

-- ============================================
-- Problem Status Enum Reference
-- ============================================
-- 0 = Pending
-- 1 = Processing
-- 2 = Completed
-- 3 = Failed

-- ============================================
-- Notes
-- ============================================
-- 1. CHAR(36) is used for GUID/UUID storage
-- 2. DATETIME(6) provides microsecond precision
-- 3. JSON type for flexible solution steps storage
-- 4. CASCADE deletes maintain referential integrity
-- 5. Indexes optimize common query patterns
-- 6. utf8mb4 supports full Unicode including emojis

SELECT 'Database created successfully!' AS Status;
