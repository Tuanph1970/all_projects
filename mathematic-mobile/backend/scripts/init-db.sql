-- Initialize Mathematics Solver Database
USE master;
GO

-- Create database if it doesn't exist
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MathematicsSolverDb')
BEGIN
    CREATE DATABASE MathematicsSolverDb;
    PRINT 'Database MathematicsSolverDb created successfully';
END
ELSE
BEGIN
    PRINT 'Database MathematicsSolverDb already exists';
END
GO

-- Create development database
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MathematicsSolverDb_Dev')
BEGIN
    CREATE DATABASE MathematicsSolverDb_Dev;
    PRINT 'Database MathematicsSolverDb_Dev created successfully';
END
ELSE
BEGIN
    PRINT 'Database MathematicsSolverDb_Dev already exists';
END
GO

-- Create production database
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MathematicsSolverDb_Prod')
BEGIN
    CREATE DATABASE MathematicsSolverDb_Prod;
    PRINT 'Database MathematicsSolverDb_Prod created successfully';
END
ELSE
BEGIN
    PRINT 'Database MathematicsSolverDb_Prod already exists';
END
GO

PRINT 'Database initialization completed successfully';
GO