-- Delete Data Warehouse Data
-- Order: Fact tables first (due to foreign keys), then Dimension tables
-- Database: CoreBanking_DW

USE CoreBanking_DW;
GO

PRINT 'Starting deletion of Data Warehouse data...';
PRINT '==========================================';
GO

-- =====================================================
-- STEP 1: DELETE FACT TABLES
-- Must be deleted first due to foreign key constraints
-- =====================================================

PRINT 'Step 1: Deleting Fact_Accuracy...';
DELETE FROM Fact_Accuracy;
GO
PRINT 'Fact_Accuracy deleted successfully.';
GO

-- =====================================================
-- STEP 2: DELETE DIMENSION TABLES
-- Order: Delete dimensions that might have dependencies
-- =====================================================

PRINT '';
PRINT 'Step 2: Deleting Dimension tables...';
GO

-- Delete Dim_Transaction
PRINT 'Deleting Dim_Transaction...';
DELETE FROM Dim_Transaction;
GO
PRINT 'Dim_Transaction deleted successfully.';
GO

-- Delete Dim_Credit
PRINT 'Deleting Dim_Credit...';
DELETE FROM Dim_Credit;
GO
PRINT 'Dim_Credit deleted successfully.';
GO

-- Delete Dim_Compte
PRINT 'Deleting Dim_Compte...';
DELETE FROM Dim_Compte;
GO
PRINT 'Dim_Compte deleted successfully.';
GO

-- Delete Dim_Client
PRINT 'Deleting Dim_Client...';
DELETE FROM Dim_Client;
GO
PRINT 'Dim_Client deleted successfully.';
GO

-- Delete Dim_Agence
PRINT 'Deleting Dim_Agence...';
DELETE FROM Dim_Agence;
GO
PRINT 'Dim_Agence deleted successfully.';
GO

-- Delete Dim_Date (last - reference table)
PRINT 'Deleting Dim_Date...';
DELETE FROM Dim_Date;
GO
PRINT 'Dim_Date deleted successfully.';
GO

-- =====================================================
-- VERIFICATION
-- =====================================================

PRINT '';
PRINT '==========================================';
PRINT 'Verifying deletion...';
PRINT '==========================================';
GO

SELECT 
    'Fact_Accuracy' AS TableName,
    COUNT(*) AS RemainingRows
FROM Fact_Accuracy
UNION ALL
SELECT 
    'Dim_Transaction' AS TableName,
    COUNT(*) AS RemainingRows
FROM Dim_Transaction
UNION ALL
SELECT 
    'Dim_Credit' AS TableName,
    COUNT(*) AS RemainingRows
FROM Dim_Credit
UNION ALL
SELECT 
    'Dim_Compte' AS TableName,
    COUNT(*) AS RemainingRows
FROM Dim_Compte
UNION ALL
SELECT 
    'Dim_Client' AS TableName,
    COUNT(*) AS RemainingRows
FROM Dim_Client
UNION ALL
SELECT 
    'Dim_Agence' AS TableName,
    COUNT(*) AS RemainingRows
FROM Dim_Agence
UNION ALL
SELECT 
    'Dim_Date' AS TableName,
    COUNT(*) AS RemainingRows
FROM Dim_Date;
GO

PRINT '';
PRINT '==========================================';
PRINT 'Data Warehouse deletion completed!';
PRINT '==========================================';
GO
