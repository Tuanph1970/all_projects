-- ============================================================================
-- Mathematics Solver Database Initialization Script
-- This script is executed automatically when MySQL container starts
-- ============================================================================

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS `MathematicsSolverDb`
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `MathematicsSolverDb`;

-- ============================================================================
-- USERS TABLE (Auth Service)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `Users` (
    `Id` INT AUTO_INCREMENT PRIMARY KEY,
    `Username` VARCHAR(50) NOT NULL UNIQUE,
    `Email` VARCHAR(100) NOT NULL UNIQUE,
    `PasswordHash` TEXT NOT NULL,
    `PhoneNumber` VARCHAR(20) NULL,
    `FullName` VARCHAR(100) NULL,
    `AvatarUrl` VARCHAR(500) NULL,
    `GradeLevel` INT NULL,
    `School` VARCHAR(200) NULL,
    `IsEmailVerified` BOOLEAN DEFAULT FALSE,
    `IsPhoneVerified` BOOLEAN DEFAULT FALSE,
    `CreatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `UpdatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `LastLoginAt` DATETIME NULL,
    `IsActive` BOOLEAN DEFAULT TRUE,
    INDEX `idx_users_email` (`Email`),
    INDEX `idx_users_username` (`Username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- REFRESH TOKENS TABLE (Auth Service)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `RefreshTokens` (
    `Id` INT AUTO_INCREMENT PRIMARY KEY,
    `UserId` INT NOT NULL,
    `Token` VARCHAR(500) NOT NULL UNIQUE,
    `ExpiresAt` DATETIME NOT NULL,
    `CreatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `RevokedAt` DATETIME NULL,
    `IsRevoked` BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (`UserId`) REFERENCES `Users`(`Id`) ON DELETE CASCADE,
    INDEX `idx_refresh_tokens_token` (`Token`),
    INDEX `idx_refresh_tokens_user` (`UserId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PROBLEMS TABLE (Problem Service)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `Problems` (
    `Id` INT AUTO_INCREMENT PRIMARY KEY,
    `UserId` INT NOT NULL,
    `Title` VARCHAR(200) NULL,
    `Description` TEXT NULL,
    `ImagePath` VARCHAR(500) NULL,
    `ExtractedText` TEXT NULL,
    `Category` VARCHAR(50) DEFAULT 'General',
    `Difficulty` VARCHAR(20) DEFAULT 'Medium',
    `Status` VARCHAR(20) DEFAULT 'Pending',
    `CreatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `UpdatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `SolvedAt` DATETIME NULL,
    FOREIGN KEY (`UserId`) REFERENCES `Users`(`Id`) ON DELETE CASCADE,
    INDEX `idx_problems_user` (`UserId`),
    INDEX `idx_problems_status` (`Status`),
    INDEX `idx_problems_category` (`Category`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PROBLEM HISTORY TABLE (Problem Service)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `ProblemHistories` (
    `Id` INT AUTO_INCREMENT PRIMARY KEY,
    `ProblemId` INT NOT NULL,
    `UserId` INT NOT NULL,
    `Action` VARCHAR(50) NOT NULL,
    `Details` TEXT NULL,
    `CreatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`ProblemId`) REFERENCES `Problems`(`Id`) ON DELETE CASCADE,
    FOREIGN KEY (`UserId`) REFERENCES `Users`(`Id`) ON DELETE CASCADE,
    INDEX `idx_problem_histories_problem` (`ProblemId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SOLUTIONS TABLE (Solution Service)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `Solutions` (
    `Id` INT AUTO_INCREMENT PRIMARY KEY,
    `ProblemId` INT NOT NULL,
    `UserId` INT NOT NULL,
    `SolutionText` TEXT NOT NULL,
    `Steps` JSON NULL,
    `Method` VARCHAR(50) DEFAULT 'symbolic',
    `Confidence` DECIMAL(5,4) DEFAULT 0.9000,
    `ProcessingTimeMs` INT DEFAULT 0,
    `CreatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`ProblemId`) REFERENCES `Problems`(`Id`) ON DELETE CASCADE,
    FOREIGN KEY (`UserId`) REFERENCES `Users`(`Id`) ON DELETE CASCADE,
    INDEX `idx_solutions_problem` (`ProblemId`),
    INDEX `idx_solutions_user` (`UserId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- FEEDBACK TABLE (Solution Service)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `Feedback` (
    `Id` INT AUTO_INCREMENT PRIMARY KEY,
    `SolutionId` INT NOT NULL,
    `UserId` INT NOT NULL,
    `Rating` INT NULL,
    `IsHelpful` BOOLEAN NULL,
    `Comment` TEXT NULL,
    `FeedbackType` VARCHAR(50) DEFAULT 'rating',
    `CreatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`SolutionId`) REFERENCES `Solutions`(`Id`) ON DELETE CASCADE,
    FOREIGN KEY (`UserId`) REFERENCES `Users`(`Id`) ON DELETE CASCADE,
    INDEX `idx_feedback_solution` (`SolutionId`),
    INDEX `idx_feedback_user` (`UserId`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- EMAIL VERIFICATION TOKENS TABLE (Auth Service)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `EmailVerificationTokens` (
    `Id` INT AUTO_INCREMENT PRIMARY KEY,
    `UserId` INT NOT NULL,
    `Token` VARCHAR(500) NOT NULL UNIQUE,
    `ExpiresAt` DATETIME NOT NULL,
    `IsUsed` BOOLEAN DEFAULT FALSE,
    `CreatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`UserId`) REFERENCES `Users`(`Id`) ON DELETE CASCADE,
    INDEX `idx_email_tokens_token` (`Token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- PASSWORD RESET TOKENS TABLE (Auth Service)
-- ============================================================================
CREATE TABLE IF NOT EXISTS `PasswordResetTokens` (
    `Id` INT AUTO_INCREMENT PRIMARY KEY,
    `UserId` INT NOT NULL,
    `Email` VARCHAR(100) NOT NULL,
    `Token` VARCHAR(500) NOT NULL UNIQUE,
    `ExpiresAt` DATETIME NOT NULL,
    `IsUsed` BOOLEAN DEFAULT FALSE,
    `CreatedAt` DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (`UserId`) REFERENCES `Users`(`Id`) ON DELETE CASCADE,
    INDEX `idx_password_tokens_token` (`Token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- SEED DATA (For Development/Testing)
-- ============================================================================

-- Insert a test user (password: Test123!)
INSERT INTO `Users` (`Username`, `Email`, `PasswordHash`, `FullName`, `GradeLevel`, `IsEmailVerified`, `CreatedAt`) 
VALUES ('testuser', 'test@example.com', '$2a$11$rW3XLrKjLLPqB8qQJzqQh.6F5K5K5K5K5K5K5K5K5K5K5K5K5K5K5', 'Test User', 11, TRUE, NOW())
ON DUPLICATE KEY UPDATE `Username` = `Username`;

-- Insert sample problems
INSERT INTO `Problems` (`UserId`, `Title`, `Description`, `Category`, `Difficulty`, `Status`, `CreatedAt`) 
VALUES 
(1, 'Sample Algebra Problem', 'Solve for x: 2x + 3 = 7', 'Algebra', 'Easy', 'Pending', NOW()),
(1, 'Sample Calculus Problem', 'Find the derivative of f(x) = x^2 + 3x', 'Calculus', 'Medium', 'Pending', NOW())
ON DUPLICATE KEY UPDATE `Title` = `Title`;

-- ============================================================================
-- END OF INITIALIZATION SCRIPT
-- ============================================================================
