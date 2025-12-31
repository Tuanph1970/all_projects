-- ============================================================================
-- Database Schema Enhancement: Model Covariate Compatibility Validation
-- Purpose: Ensure indicator covariate_type is compatible with model capabilities
-- Date: 2025-10-09
-- ============================================================================

-- ============================================================================
-- STEP 1: Create validation function
-- ============================================================================

DELIMITER //

DROP FUNCTION IF EXISTS validate_covariate_compatibility//

CREATE FUNCTION validate_covariate_compatibility(
    p_solution_id INT,
    p_covariate_type VARCHAR(10)
) RETURNS BOOLEAN
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE v_model_id INT;
    DECLARE v_supports_past TINYINT(1);
    DECLARE v_supports_future TINYINT(1);
    DECLARE v_is_valid BOOLEAN DEFAULT FALSE;

    -- Get model for this solution
    SELECT model_id INTO v_model_id
    FROM tbl_solution
    WHERE id = p_solution_id;

    -- If solution doesn't exist, return false
    IF v_model_id IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Get model capabilities
    SELECT past_covariate, future_covariate
    INTO v_supports_past, v_supports_future
    FROM tbl_model
    WHERE id = v_model_id;

    -- Validate based on covariate_type
    IF p_covariate_type = 'past' THEN
        SET v_is_valid = (v_supports_past = 1);
    ELSEIF p_covariate_type = 'future' THEN
        SET v_is_valid = (v_supports_future = 1);
    ELSEIF p_covariate_type = 'both' THEN
        SET v_is_valid = (v_supports_past = 1 AND v_supports_future = 1);
    ELSE
        SET v_is_valid = FALSE;
    END IF;

    RETURN v_is_valid;
END//

DELIMITER ;

-- ============================================================================
-- STEP 2: Create trigger to validate on INSERT
-- ============================================================================

DELIMITER //

DROP TRIGGER IF EXISTS trg_solution_indicators_before_insert//

CREATE TRIGGER trg_solution_indicators_before_insert
BEFORE INSERT ON solution_indicators
FOR EACH ROW
BEGIN
    DECLARE v_is_valid BOOLEAN;
    DECLARE v_error_msg VARCHAR(255);
    DECLARE v_model_name VARCHAR(100);

    -- Validate covariate compatibility
    SET v_is_valid = validate_covariate_compatibility(NEW.solution_id, NEW.covariate_type);

    IF NOT v_is_valid THEN
        -- Get model name for better error message
        SELECT m.model_name INTO v_model_name
        FROM tbl_solution s
        INNER JOIN tbl_model m ON s.model_id = m.id
        WHERE s.id = NEW.solution_id;

        SET v_error_msg = CONCAT(
            'Covariate type "', NEW.covariate_type,
            '" is incompatible with model "', COALESCE(v_model_name, 'Unknown'),
            '". Check model past_covariate and future_covariate capabilities.'
        );

        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = v_error_msg;
    END IF;
END//

DELIMITER ;

-- ============================================================================
-- STEP 3: Create trigger to validate on UPDATE
-- ============================================================================

DELIMITER //

DROP TRIGGER IF EXISTS trg_solution_indicators_before_update//

CREATE TRIGGER trg_solution_indicators_before_update
BEFORE UPDATE ON solution_indicators
FOR EACH ROW
BEGIN
    DECLARE v_is_valid BOOLEAN;
    DECLARE v_error_msg VARCHAR(255);
    DECLARE v_model_name VARCHAR(100);

    -- Only validate if covariate_type is being changed
    IF NEW.covariate_type != OLD.covariate_type THEN
        -- Validate covariate compatibility
        SET v_is_valid = validate_covariate_compatibility(NEW.solution_id, NEW.covariate_type);

        IF NOT v_is_valid THEN
            -- Get model name for better error message
            SELECT m.model_name INTO v_model_name
            FROM tbl_solution s
            INNER JOIN tbl_model m ON s.model_id = m.id
            WHERE s.id = NEW.solution_id;

            SET v_error_msg = CONCAT(
                'Covariate type "', NEW.covariate_type,
                '" is incompatible with model "', COALESCE(v_model_name, 'Unknown'),
                '". Check model past_covariate and future_covariate capabilities.'
            );

            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = v_error_msg;
        END IF;
    END IF;
END//

DELIMITER ;

-- ============================================================================
-- STEP 4: Create helper stored procedure for validation
-- ============================================================================

DELIMITER //

DROP PROCEDURE IF EXISTS sp_check_solution_covariate_compatibility//

CREATE PROCEDURE sp_check_solution_covariate_compatibility(IN p_solution_id INT)
BEGIN
    SELECT
        si.id AS indicator_mapping_id,
        si.solution_id,
        s.solution_name,
        m.model_name,
        m.past_covariate AS model_supports_past,
        m.future_covariate AS model_supports_future,
        ti.name AS indicator_name,
        si.indicator_category,
        si.covariate_type,
        CASE
            WHEN si.covariate_type = 'past' AND m.past_covariate = 1 THEN 'VALID'
            WHEN si.covariate_type = 'future' AND m.future_covariate = 1 THEN 'VALID'
            WHEN si.covariate_type = 'both' AND m.past_covariate = 1 AND m.future_covariate = 1 THEN 'VALID'
            ELSE 'INVALID'
        END AS compatibility_status,
        CASE
            WHEN si.covariate_type = 'past' AND m.past_covariate = 0 THEN 'Model does not support past covariates'
            WHEN si.covariate_type = 'future' AND m.future_covariate = 0 THEN 'Model does not support future covariates'
            WHEN si.covariate_type = 'both' AND m.past_covariate = 0 THEN 'Model does not support past covariates (required for "both")'
            WHEN si.covariate_type = 'both' AND m.future_covariate = 0 THEN 'Model does not support future covariates (required for "both")'
            ELSE 'Compatible'
        END AS issue_description
    FROM solution_indicators si
    INNER JOIN tbl_solution s ON si.solution_id = s.id
    INNER JOIN tbl_model m ON s.model_id = m.id
    INNER JOIN technical_indicators ti ON si.indicator_id = ti.id
    WHERE si.solution_id = p_solution_id
    ORDER BY si.indicator_category;
END//

DELIMITER ;

-- ============================================================================
-- STEP 5: Create view for covariate compatibility audit
-- ============================================================================

CREATE OR REPLACE VIEW v_covariate_compatibility_audit AS
SELECT
    si.id AS indicator_mapping_id,
    si.solution_id,
    s.solution_name,
    s.ticker,
    m.model_name,
    m.model_type,
    m.past_covariate AS model_supports_past,
    m.future_covariate AS model_supports_future,
    ti.name AS indicator_name,
    si.indicator_category,
    si.covariate_type,
    CASE
        WHEN si.covariate_type = 'past' AND m.past_covariate = 1 THEN 'VALID'
        WHEN si.covariate_type = 'future' AND m.future_covariate = 1 THEN 'VALID'
        WHEN si.covariate_type = 'both' AND m.past_covariate = 1 AND m.future_covariate = 1 THEN 'VALID'
        ELSE 'INVALID'
    END AS compatibility_status
FROM solution_indicators si
INNER JOIN tbl_solution s ON si.solution_id = s.id
INNER JOIN tbl_model m ON s.model_id = m.id
INNER JOIN technical_indicators ti ON si.indicator_id = ti.id;

-- ============================================================================
-- STEP 6: Add table comments
-- ============================================================================

ALTER TABLE solution_indicators COMMENT = 'Links solutions to indicators. Covariate type must be compatible with model capabilities (enforced by triggers).';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Check all solutions for covariate compatibility
-- SELECT * FROM v_covariate_compatibility_audit WHERE compatibility_status = 'INVALID';

-- Check specific solution
-- CALL sp_check_solution_covariate_compatibility(1);

-- Test validation function
-- SELECT validate_covariate_compatibility(1, 'past') AS is_past_valid;
-- SELECT validate_covariate_compatibility(1, 'future') AS is_future_valid;
-- SELECT validate_covariate_compatibility(1, 'both') AS is_both_valid;

-- ============================================================================
-- EXAMPLE: Testing the validation
-- ============================================================================

/*
-- Assume solution 1 uses model 1 which only supports past covariates:
-- past_covariate=1, future_covariate=0

-- This should SUCCEED
INSERT INTO solution_indicators (solution_id, indicator_id, indicator_category, covariate_type)
VALUES (1, 1, 'trend', 'past');

-- This should FAIL with error message
INSERT INTO solution_indicators (solution_id, indicator_id, indicator_category, covariate_type)
VALUES (1, 2, 'momentum', 'future');
-- Error: Covariate type "future" is incompatible with model "LSTM Basic"

-- This should FAIL with error message
INSERT INTO solution_indicators (solution_id, indicator_id, indicator_category, covariate_type)
VALUES (1, 3, 'volatility', 'both');
-- Error: Covariate type "both" is incompatible with model "LSTM Basic"
*/

-- ============================================================================
-- ROLLBACK SCRIPT (if needed)
-- ============================================================================

/*
-- To rollback this migration:

DROP TRIGGER IF EXISTS trg_solution_indicators_before_insert;
DROP TRIGGER IF EXISTS trg_solution_indicators_before_update;
DROP FUNCTION IF EXISTS validate_covariate_compatibility;
DROP PROCEDURE IF EXISTS sp_check_solution_covariate_compatibility;
DROP VIEW IF EXISTS v_covariate_compatibility_audit;
*/
