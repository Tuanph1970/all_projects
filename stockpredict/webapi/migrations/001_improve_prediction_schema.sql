-- ============================================================================
-- Database Schema Migration: Improved Prediction System
-- Purpose: Simplify and clarify the prediction solution schema
-- Date: 2025-10-09
-- ============================================================================

-- ============================================================================
-- STEP 1: Add new fields to existing tables (backward compatible)
-- ============================================================================

-- Add train_validation_ratio to tbl_solution
ALTER TABLE tbl_solution
ADD COLUMN IF NOT EXISTS train_validation_ratio DECIMAL(3,2) DEFAULT 0.80
COMMENT 'Training/validation split ratio (e.g., 0.80 = 80% train, 20% validation)';

-- Add covariate_type to solution_indicators
ALTER TABLE solution_indicators
ADD COLUMN IF NOT EXISTS covariate_type ENUM('past', 'future', 'both') DEFAULT 'past'
COMMENT 'Whether indicator is used as past covariate, future covariate, or both';

-- Rename indicator_type to indicator_category for clarity
ALTER TABLE solution_indicators
CHANGE COLUMN indicator_type indicator_category ENUM('trend', 'momentum', 'volatility', 'volume') NOT NULL
COMMENT 'Category of technical indicator';

-- Add timestamps to solution_indicators if not exists
ALTER TABLE solution_indicators
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- Add timestamps to technical_indicators if not exists
ALTER TABLE technical_indicators
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- ============================================================================
-- STEP 2: Update constraints
-- ============================================================================

-- Drop old constraint if exists
ALTER TABLE solution_indicators DROP INDEX IF EXISTS unique_solution_indicator;

-- Add new UNIQUE constraint: one indicator per category per solution
ALTER TABLE solution_indicators
ADD UNIQUE KEY unique_solution_indicator_category (solution_id, indicator_category);

-- Add index for better query performance
ALTER TABLE solution_indicators
ADD INDEX idx_solution_id (solution_id);

ALTER TABLE solution_indicators
ADD INDEX idx_indicator_category (indicator_category);

-- ============================================================================
-- STEP 3: Rename tbl_model to models for consistency (optional but recommended)
-- ============================================================================

-- Check if models table doesn't exist, then rename
-- Note: Comment out if you want to keep tbl_model name for backward compatibility
-- RENAME TABLE tbl_model TO models;

-- If renaming, also update column names for clarity
-- ALTER TABLE models
-- CHANGE COLUMN past_covariate supports_past_covariates TINYINT(1) DEFAULT 0,
-- CHANGE COLUMN future_covariate supports_future_covariates TINYINT(1) DEFAULT 0;

-- ============================================================================
-- STEP 4: Data validation and cleanup
-- ============================================================================

-- Ensure all indicators have valid categories
UPDATE solution_indicators
SET indicator_category = (
    SELECT type FROM technical_indicators
    WHERE technical_indicators.id = solution_indicators.indicator_id
)
WHERE indicator_category IS NULL OR indicator_category = '';

-- ============================================================================
-- STEP 5: Create views for easier querying (optional but helpful)
-- ============================================================================

-- View: Complete solution details with all indicators
CREATE OR REPLACE VIEW v_solution_complete AS
SELECT
    s.id AS solution_id,
    s.solution_name,
    s.ticker,
    s.status,
    s.solution_status,
    s.start_training_date,
    s.end_training_date,
    s.train_validation_ratio,
    s.created_date,
    s.created_by,
    m.id AS model_id,
    m.model_name,
    m.model_type,
    m.past_covariate AS supports_past_covariates,
    m.future_covariate AS supports_future_covariates,
    -- Trend indicator
    ti_trend.id AS trend_indicator_id,
    ti_trend.name AS trend_indicator_name,
    si_trend.covariate_type AS trend_covariate_type,
    si_trend.parameters AS trend_parameters,
    -- Momentum indicator
    ti_momentum.id AS momentum_indicator_id,
    ti_momentum.name AS momentum_indicator_name,
    si_momentum.covariate_type AS momentum_covariate_type,
    si_momentum.parameters AS momentum_parameters,
    -- Volatility indicator
    ti_volatility.id AS volatility_indicator_id,
    ti_volatility.name AS volatility_indicator_name,
    si_volatility.covariate_type AS volatility_covariate_type,
    si_volatility.parameters AS volatility_parameters,
    -- Volume indicator
    ti_volume.id AS volume_indicator_id,
    ti_volume.name AS volume_indicator_name,
    si_volume.covariate_type AS volume_covariate_type,
    si_volume.parameters AS volume_parameters
FROM tbl_solution s
INNER JOIN tbl_model m ON s.model_id = m.id
LEFT JOIN solution_indicators si_trend ON s.id = si_trend.solution_id AND si_trend.indicator_category = 'trend'
LEFT JOIN technical_indicators ti_trend ON si_trend.indicator_id = ti_trend.id
LEFT JOIN solution_indicators si_momentum ON s.id = si_momentum.solution_id AND si_momentum.indicator_category = 'momentum'
LEFT JOIN technical_indicators ti_momentum ON si_momentum.indicator_id = ti_momentum.id
LEFT JOIN solution_indicators si_volatility ON s.id = si_volatility.solution_id AND si_volatility.indicator_category = 'volatility'
LEFT JOIN technical_indicators ti_volatility ON si_volatility.indicator_id = ti_volatility.id
LEFT JOIN solution_indicators si_volume ON s.id = si_volume.solution_id AND si_volume.indicator_category = 'volume'
LEFT JOIN technical_indicators ti_volume ON si_volume.indicator_id = ti_volume.id;

-- View: Solution validation status
CREATE OR REPLACE VIEW v_solution_validation AS
SELECT
    s.id AS solution_id,
    s.solution_name,
    s.ticker,
    COUNT(DISTINCT si.indicator_category) AS configured_indicators,
    MAX(CASE WHEN si.indicator_category = 'trend' THEN 1 ELSE 0 END) AS has_trend,
    MAX(CASE WHEN si.indicator_category = 'momentum' THEN 1 ELSE 0 END) AS has_momentum,
    MAX(CASE WHEN si.indicator_category = 'volatility' THEN 1 ELSE 0 END) AS has_volatility,
    MAX(CASE WHEN si.indicator_category = 'volume' THEN 1 ELSE 0 END) AS has_volume,
    CASE
        WHEN COUNT(DISTINCT si.indicator_category) = 4 THEN 'COMPLETE'
        WHEN COUNT(DISTINCT si.indicator_category) > 0 THEN 'INCOMPLETE'
        ELSE 'NOT_CONFIGURED'
    END AS configuration_status
FROM tbl_solution s
LEFT JOIN solution_indicators si ON s.id = si.solution_id
GROUP BY s.id, s.solution_name, s.ticker;

-- ============================================================================
-- STEP 6: Add stored procedure for solution validation (optional)
-- ============================================================================

DELIMITER //

CREATE PROCEDURE IF NOT EXISTS sp_validate_solution_indicators(IN p_solution_id INT)
BEGIN
    SELECT
        p_solution_id AS solution_id,
        COUNT(DISTINCT indicator_category) AS configured_count,
        CASE
            WHEN COUNT(DISTINCT indicator_category) = 4 THEN TRUE
            ELSE FALSE
        END AS is_valid,
        GROUP_CONCAT(DISTINCT indicator_category ORDER BY indicator_category) AS configured_categories,
        CASE
            WHEN COUNT(DISTINCT CASE WHEN indicator_category = 'trend' THEN 1 END) = 0 THEN 'trend,'
            ELSE ''
        END ||
        CASE
            WHEN COUNT(DISTINCT CASE WHEN indicator_category = 'momentum' THEN 1 END) = 0 THEN 'momentum,'
            ELSE ''
        END ||
        CASE
            WHEN COUNT(DISTINCT CASE WHEN indicator_category = 'volatility' THEN 1 END) = 0 THEN 'volatility,'
            ELSE ''
        END ||
        CASE
            WHEN COUNT(DISTINCT CASE WHEN indicator_category = 'volume' THEN 1 END) = 0 THEN 'volume'
            ELSE ''
        END AS missing_categories
    FROM solution_indicators
    WHERE solution_id = p_solution_id;
END //

DELIMITER ;

-- ============================================================================
-- STEP 7: Comments and documentation
-- ============================================================================

-- Add table comments
ALTER TABLE tbl_solution COMMENT = 'Prediction solutions: model + ticker + 4 indicators';
ALTER TABLE technical_indicators COMMENT = 'Template library of technical indicators';
ALTER TABLE solution_indicators COMMENT = 'Links solutions to indicators with custom parameters and covariate types';
ALTER TABLE tbl_model COMMENT = 'Machine learning models (RNN, LSTM, XGBoost) with covariate support flags';

-- Add column comments
ALTER TABLE tbl_solution
MODIFY COLUMN ticker VARCHAR(20) COMMENT 'Stock symbol (e.g., TCB, FPT, ICT)',
MODIFY COLUMN start_training_date DATE COMMENT 'Training period start date',
MODIFY COLUMN end_training_date DATE COMMENT 'Training period end date',
MODIFY COLUMN solution_status INT COMMENT '0=not trained, 1=training, 2=trained, 3=error';

ALTER TABLE solution_indicators
MODIFY COLUMN parameters JSON COMMENT 'Custom indicator parameters (overrides template defaults)',
MODIFY COLUMN indicator_category ENUM('trend', 'momentum', 'volatility', 'volume') COMMENT 'One indicator per category required';

ALTER TABLE technical_indicators
MODIFY COLUMN type ENUM('trend', 'momentum', 'volatility', 'volume') COMMENT 'Indicator category',
MODIFY COLUMN default_parameters JSON COMMENT 'Default calculation parameters';

-- ============================================================================
-- STEP 8: Backward compatibility notes
-- ============================================================================

-- Tables tbl_time_series and time_series_solution are now DEPRECATED
-- Keep them temporarily for data migration but new solutions should NOT use them
-- They will be removed in a future migration after all data is migrated

-- Mark deprecated tables with comments
ALTER TABLE tbl_time_series COMMENT = 'DEPRECATED: Use solution_indicators instead. Will be removed in future version.';
ALTER TABLE time_series_solution COMMENT = 'DEPRECATED: Use solution_indicators with covariate_type instead. Will be removed in future version.';

-- ============================================================================
-- VERIFICATION QUERIES (run these to verify migration)
-- ============================================================================

-- Check solution_indicators structure
-- DESCRIBE solution_indicators;

-- Check for solutions with incomplete indicator configuration
-- SELECT * FROM v_solution_validation WHERE configuration_status != 'COMPLETE';

-- Check all solutions
-- SELECT * FROM v_solution_complete;

-- Validate a specific solution
-- CALL sp_validate_solution_indicators(1);

-- ============================================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================================

/*
-- To rollback this migration:

ALTER TABLE tbl_solution DROP COLUMN IF EXISTS train_validation_ratio;
ALTER TABLE solution_indicators DROP COLUMN IF EXISTS covariate_type;
ALTER TABLE solution_indicators DROP COLUMN IF EXISTS created_at;
ALTER TABLE solution_indicators DROP COLUMN IF EXISTS updated_at;
ALTER TABLE solution_indicators CHANGE COLUMN indicator_category indicator_type VARCHAR(50);
ALTER TABLE solution_indicators DROP INDEX IF EXISTS unique_solution_indicator_category;
ALTER TABLE solution_indicators DROP INDEX IF EXISTS idx_solution_id;
ALTER TABLE solution_indicators DROP INDEX IF EXISTS idx_indicator_category;
DROP VIEW IF EXISTS v_solution_complete;
DROP VIEW IF EXISTS v_solution_validation;
DROP PROCEDURE IF EXISTS sp_validate_solution_indicators;
*/
