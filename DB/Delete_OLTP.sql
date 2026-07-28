-- Delete OLTP Database Data
-- Database: CoreBanking_OLTP
-- Order: Delete tables with foreign key dependencies last

USE CoreBanking_OLTP;
GO

PRINT 'Starting deletion of OLTP database data...';
PRINT '==========================================';
GO

-- =====================================================
-- STEP 1: DELETE TRANSACTION TABLES (depend on Compte)
-- =====================================================

PRINT 'Step 1: Deleting Transaction_Bancaire...';
DELETE FROM Transaction_Bancaire;
GO
PRINT 'Transaction_Bancaire deleted successfully.';
GO

-- =====================================================
-- STEP 2: DELETE REMBOURSEMENT TABLES (depend on Credit)
-- =====================================================

PRINT 'Step 2: Deleting Remboursement...';
DELETE FROM Remboursement;
GO
PRINT 'Remboursement deleted successfully.';
GO

-- =====================================================
-- STEP 3: DELETE CREDIT TABLES (depend on Client)
-- =====================================================

PRINT 'Step 3: Deleting Credit...';
DELETE FROM Credit;
GO
PRINT 'Credit deleted successfully.';
GO

-- =====================================================
-- STEP 4: DELETE CARTE TABLES (depend on Compte)
-- =====================================================

PRINT 'Step 4: Deleting Carte...';
DELETE FROM Carte;
GO
PRINT 'Carte deleted successfully.';
GO

-- =====================================================
-- STEP 5: DELETE VIREMENT TABLES (depend on Compte)
-- =====================================================

PRINT 'Step 5: Deleting Virement...';
DELETE FROM Virement;
GO
PRINT 'Virement deleted successfully.';
GO

-- =====================================================
-- STEP 6: DELETE HISTORIQUE_SOLDE TABLES (depend on Compte)
-- =====================================================

PRINT 'Step 6: Deleting Historique_Solde...';
DELETE FROM Historique_Solde;
GO
PRINT 'Historique_Solde deleted successfully.';
GO

-- =====================================================
-- STEP 7: DELETE COMPTE TABLES (depend on Client, Type_Compte, Devise)
-- =====================================================

PRINT 'Step 7: Deleting Compte...';
DELETE FROM Compte;
GO
PRINT 'Compte deleted successfully.';
GO

-- =====================================================
-- STEP 8: DELETE CLIENT TABLES (depend on Type_Client, Agence)
-- =====================================================

PRINT 'Step 8: Deleting Client...';
DELETE FROM Client;
GO
PRINT 'Client deleted successfully.';
GO

-- =====================================================
-- STEP 9: DELETE EMPLOYE TABLES (depend on Agence)
-- =====================================================

PRINT 'Step 9: Deleting Employe...';
DELETE FROM Employe;
GO
PRINT 'Employe deleted successfully.';
GO

-- =====================================================
-- STEP 10: DELETE REFERENCE TABLES
-- =====================================================

PRINT 'Step 10: Deleting reference tables...';
GO

-- Delete Canal_Transaction
PRINT 'Deleting Canal_Transaction...';
DELETE FROM Canal_Transaction;
GO
PRINT 'Canal_Transaction deleted successfully.';
GO

-- Delete Type_Compte
PRINT 'Deleting Type_Compte...';
DELETE FROM Type_Compte;
GO
PRINT 'Type_Compte deleted successfully.';
GO

-- Delete Devise
PRINT 'Deleting Devise...';
DELETE FROM Devise;
GO
PRINT 'Devise deleted successfully.';
GO

-- Delete Type_Client
PRINT 'Deleting Type_Client...';
DELETE FROM Type_Client;
GO
PRINT 'Type_Client deleted successfully.';
GO

-- Delete Agence (last - reference table)
PRINT 'Deleting Agence...';
DELETE FROM Agence;
GO
PRINT 'Agence deleted successfully.';
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
    'Transaction_Bancaire' AS TableName,
    COUNT(*) AS RemainingRows
FROM Transaction_Bancaire
UNION ALL
SELECT 
    'Remboursement' AS TableName,
    COUNT(*) AS RemainingRows
FROM Remboursement
UNION ALL
SELECT 
    'Credit' AS TableName,
    COUNT(*) AS RemainingRows
FROM Credit
UNION ALL
SELECT 
    'Carte' AS TableName,
    COUNT(*) AS RemainingRows
FROM Carte
UNION ALL
SELECT 
    'Virement' AS TableName,
    COUNT(*) AS RemainingRows
FROM Virement
UNION ALL
SELECT 
    'Historique_Solde' AS TableName,
    COUNT(*) AS RemainingRows
FROM Historique_Solde
UNION ALL
SELECT 
    'Compte' AS TableName,
    COUNT(*) AS RemainingRows
FROM Compte
UNION ALL
SELECT 
    'Client' AS TableName,
    COUNT(*) AS RemainingRows
FROM Client
UNION ALL
SELECT 
    'Employe' AS TableName,
    COUNT(*) AS RemainingRows
FROM Employe
UNION ALL
SELECT 
    'Canal_Transaction' AS TableName,
    COUNT(*) AS RemainingRows
FROM Canal_Transaction
UNION ALL
SELECT 
    'Type_Compte' AS TableName,
    COUNT(*) AS RemainingRows
FROM Type_Compte
UNION ALL
SELECT 
    'Devise' AS TableName,
    COUNT(*) AS RemainingRows
FROM Devise
UNION ALL
SELECT 
    'Type_Client' AS TableName,
    COUNT(*) AS RemainingRows
FROM Type_Client
UNION ALL
SELECT 
    'Agence' AS TableName,
    COUNT(*) AS RemainingRows
FROM Agence;
GO

PRINT '';
PRINT '==========================================';
PRINT 'OLTP database deletion completed!';
PRINT '==========================================';
GO
