"""
Data Quality Engine for Compte Domain
Performs accuracy checks on OLTP.Compte table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataQuality.data_quality_engine import BaseQualityEngine, QualityIssue
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CompteQualityEngine(BaseQualityEngine):
    """Quality engine for Compte domain accuracy checks"""
    
    def __init__(self, oltp_conn, dwh_conn):
        super().__init__(oltp_conn, dwh_conn)
    
    def run_all_checks(self) -> dict:
        """Run all accuracy checks for Compte domain"""
        logger.info("Starting Compte domain accuracy checks...")
        
        results = {
            'solde_extreme_values': 0,
            'solde_decimal_precision': 0,
            'date_ouverture_reasonable': 0,
            'statut_business_logic': 0,
            'total_issues': 0
        }
        
        # Accuracy Check 1: Solde extreme values (unrealistically high or low)
        query = """
        SELECT Compte_ID, Solde 
        FROM CoreBanking_OLTP.dbo.Compte 
        WHERE Solde IS NOT NULL 
        AND (ABS(Solde) > 1000000000 OR (ABS(Solde) < 0.01 AND Solde <> 0))
        """
        results['solde_extreme_values'] = self.check_accuracy_validation(
            'Compte', 'Solde', query, 'Between -1B and 1B, minimum 0.01 precision', 'High',
            'Account balance has extreme values that may indicate data entry errors'
        )
        
        # Accuracy Check 2: Solde decimal precision (too many decimal places)
        query = """
        SELECT Compte_ID, Solde 
        FROM CoreBanking_OLTP.dbo.Compte 
        WHERE Solde IS NOT NULL 
        AND Solde <> ROUND(Solde, 3)
        """
        results['solde_decimal_precision'] = self.check_accuracy_validation(
            'Compte', 'Solde', query, 'Maximum 3 decimal places', 'Medium',
            'Account balance should not exceed 3 decimal places for currency accuracy'
        )
        
        # Accuracy Check 3: Date_Ouverture reasonable (not in future, not before bank establishment)
        query = """
        SELECT Compte_ID, Date_Ouverture 
        FROM CoreBanking_OLTP.dbo.Compte 
        WHERE Date_Ouverture IS NOT NULL 
        AND (Date_Ouverture > GETDATE() OR Date_Ouverture < '1950-01-01')
        """
        results['date_ouverture_reasonable'] = self.check_accuracy_validation(
            'Compte', 'Date_Ouverture', query, 'Between 1950-01-01 and current date', 'High',
            'Account opening date must be reasonable (not in future, not before bank establishment)'
        )
        
        # Accuracy Check 4: Statut business logic accuracy
        query = """
        SELECT c.Compte_ID, c.Statut, c.Solde
        FROM CoreBanking_OLTP.dbo.Compte c
        WHERE c.Statut = 'Cloture' AND c.Solde <> 0
        """
        results['statut_business_logic'] = self.check_accuracy_validation(
            'Compte', 'Statut', query, 'Closed accounts should have zero balance', 'High',
            'Closed accounts with non-zero balance indicate data inconsistency'
        )
        
        # Enrich issues with dimension keys
        self.enrich_issues_with_dimension_keys()
        
        results['total_issues'] = self.get_issues_count()
        logger.info(f"Compte quality checks completed. Total issues: {results['total_issues']}")
        
        return results
    
    def enrich_issues_with_dimension_keys(self):
        """Enrich quality issues with dimension keys from DW"""
        for issue in self.issues:
            try:
                # Get compte info from OLTP to find dimension keys
                query = f"""
                SELECT Numero_Compte, Client_ID 
                FROM CoreBanking_OLTP.dbo.Compte 
                WHERE Compte_ID = {issue.ligne_id}
                """
                results = self.oltp_conn.execute_query(query)
                
                if results:
                    numero_compte = results[0][0]
                    client_id = results[0][1]
                    
                    # Get Compte_Key from DW
                    compte_key = self.get_compte_key_by_numero(numero_compte)
                    issue.compte_key = compte_key
                    
                    # Get Client_Key and Agence_Key from DW via Client
                    if client_id:
                        client_query = f"SELECT CIN, Agence_ID FROM CoreBanking_OLTP.dbo.Client WHERE Client_ID = {client_id}"
                        client_results = self.oltp_conn.execute_query(client_query)
                        if client_results:
                            cin = client_results[0][0]
                            agence_id = client_results[0][1]
                            
                            issue.client_key = self.get_client_key_by_cin(cin)
                            
                            if agence_id:
                                agence_query = f"SELECT Code_Agence FROM CoreBanking_OLTP.dbo.Agence WHERE Agence_ID = {agence_id}"
                                agence_results = self.oltp_conn.execute_query(agence_query)
                                if agence_results:
                                    issue.agence_key = self.get_agence_key_by_code(agence_results[0][0])
                
            except Exception as e:
                logger.warning(f"Could not enrich issue {issue.ligne_id}: {e}")


if __name__ == "__main__":
    from db_connection import OLTPConnection, DWHConnection
    
    config = {
        "dwh_server": "localhost",
        "dwh_database": "CoreBanking_DW",
        "oltp_server": "localhost",
        "oltp_database": "CoreBanking_OLTP",
        "trusted_connection": "yes",
        "username": "",
        "password": ""
    }
    
    oltp_conn = OLTPConnection(config)
    dwh_conn = DWHConnection(config)
    
    try:
        oltp_conn.connect()
        dwh_conn.connect()
        
        engine = CompteQualityEngine(oltp_conn, dwh_conn)
        results = engine.run_all_checks()
        
        print("\nCompte Quality Check Results:")
        for check, count in results.items():
            print(f"  {check}: {count}")
        
    finally:
        oltp_conn.disconnect()
        dwh_conn.disconnect()
