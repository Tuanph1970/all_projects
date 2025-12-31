-- Migration Script: Update Time Series Schema to use Indicators
-- Date: 2025-10-08
-- Description:
--   1. Remove start_date column (keep only end_date)
--   2. Remove series_type_id and replace with indicator_id
--   3. Add foreign key to technical_indicators

-- Step 1: Add new indicator_id column
ALTER TABLE tbl_time_series
ADD COLUMN indicator_id INT NULL AFTER series_type_id;

-- Step 2: Add foreign key constraint to technical indicators table
-- Note: Adjust the referenced table name if different
ALTER TABLE tbl_time_series
ADD CONSTRAINT fk_time_series_indicator
FOREIGN KEY (indicator_id) REFERENCES technical_indicators(id)
ON DELETE RESTRICT ON UPDATE CASCADE;

-- Step 3: Migrate existing data (if needed)
-- This assumes you want to keep existing records with NULL indicator_id
-- You may need to manually map series_type_id to indicator_id based on your business logic
-- Example migration (adjust as needed):
-- UPDATE tbl_time_series SET indicator_id = 1 WHERE series_type_id = 1;

-- Step 4: Drop the old series_type_id column
-- WARNING: Only run this after migrating data and verifying everything works
-- ALTER TABLE tbl_time_series DROP COLUMN series_type_id;

-- Step 5: Drop start_date column
ALTER TABLE tbl_time_series DROP COLUMN start_date;

-- Step 6: Make indicator_id NOT NULL after migration
-- WARNING: Only run this after all records have valid indicator_id values
-- ALTER TABLE tbl_time_series MODIFY COLUMN indicator_id INT NOT NULL;

-- Step 7: Add index for better query performance
ALTER TABLE tbl_time_series ADD INDEX idx_indicator_id (indicator_id);

-- Step 8: Update time_series_solution table if it references series_type
-- Check if time_series_solution needs updates

-- Rollback script (save separately for safety):
/*
-- ROLLBACK SCRIPT - Run only if you need to revert changes

-- Add back start_date column
ALTER TABLE tbl_time_series ADD COLUMN start_date DATE NULL;

-- Remove indicator_id index
ALTER TABLE tbl_time_series DROP INDEX idx_indicator_id;

-- Drop foreign key constraint
ALTER TABLE tbl_time_series DROP FOREIGN KEY fk_time_series_indicator;

-- Remove indicator_id column
ALTER TABLE tbl_time_series DROP COLUMN indicator_id;

-- Re-add series_type_id if it was dropped
-- ALTER TABLE tbl_time_series ADD COLUMN series_type_id INT;
*/

-- Verification Queries:
-- 1. Check table structure
-- DESCRIBE tbl_time_series;

-- 2. Verify data migration
-- SELECT id, series_name, indicator_id, end_date FROM tbl_time_series;

-- 3. Check foreign key constraints
-- SELECT
--   CONSTRAINT_NAME,
--   TABLE_NAME,
--   COLUMN_NAME,
--   REFERENCED_TABLE_NAME,
--   REFERENCED_COLUMN_NAME
-- FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
-- WHERE TABLE_NAME = 'tbl_time_series'
-- AND CONSTRAINT_NAME LIKE 'fk%';
