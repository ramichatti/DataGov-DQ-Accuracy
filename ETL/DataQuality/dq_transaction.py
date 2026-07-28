"""
Data Quality Engine for Transaction Domain
Performs accuracy checks on OLTP.Transaction_Bancaire table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataQuality.data_quality_engine import BaseQualityEngine, QualityIssue
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TransactionQualityEngine(BaseQualityEngine):
    """Quality engine for Transaction domain accuracy checks"""
    
    def __init__(self, oltp_conn, dwh_conn):
        super().__init__(oltp_conn, dwh_conn)
    
    def run_all_checks(self) -> dict:
        """Run all accuracy checks for Transaction domain"""
        logger.info("Starting Transaction domain accuracy checks...")
        
        results = {
            'montant_extreme_values': 0,
            'montant_decimal_precision': 0,
            'date_transaction_reasonable': 0,
            'montant_type_consistency': 0,
            'total_issues': 0
        }
        
        # Accuracy Check 1: Montant extreme values (unrealistically high)
        query = """
        SELECT Transaction_ID, Montant 
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire 
        WHERE Montant IS NOT NULL 
        AND ABS(Montant) > 100000000
        """
        results['montant_extreme_values'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Montant', query, 'Between -100M and 100M', 'High',
            'Transaction amount has extreme values that may indicate data entry errors'
        )
        
        # Accuracy Check 2: Montant decimal precision (too many decimal places)
        query = """
        SELECT Transaction_ID, Montant 
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire 
        WHERE Montant IS NOT NULL 
        AND Montant <> ROUND(Montant, 3)
        """
        results['montant_decimal_precision'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Montant', query, 'Maximum 3 decimal places', 'Medium',
            'Transaction amount should not exceed 3 decimal places for currency accuracy'
        )
        
        # Accuracy Check 3: Date_Transaction reasonable (not in future, not too old)
        query = """
        SELECT Transaction_ID, Date_Transaction 
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire 
        WHERE Date_Transaction IS NOT NULL 
        AND (Date_Transaction > GETDATE() OR Date_Transaction < '2000-01-01')
        """
        results['date_transaction_reasonable'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Date_Transaction', query, 'Between 2000-01-01 and current date', 'High',
            'Transaction date must be reasonable (not in future, not before year 2000)'
        )
        
        # Accuracy Check 4: Montant and Type_Transaction consistency
        query = """
        SELECT Transaction_ID, Montant, Type_Transaction 
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire 
        WHERE Type_Transaction = 'Virement' AND Montant <= 0
        """
        results['montant_type_consistency'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Montant', query, 'Virement transactions must have positive amount', 'High',
            'Transfer transactions with non-positive amounts indicate data inconsistency'
        )
        
        # Enrich issues with dimension keys
        self.enrich_issues_with_dimension_keys()
        
        results['total_issues'] = self.get_issues_count()
        logger.info(f"Transaction quality checks completed. Total issues: {results['total_issues']}")
        
        return results
    
    def enrich_issues_with_dimension_keys(self):
        """Enrich quality issues with dimension keys from DW"""
        for issue in self.issues:
            try:
                # Get transaction info from OLTP to find dimension keys
                query = f"""
                SELECT Compte_ID, Date_Transaction 
                FROM CoreBanking_OLTP.dbo.Transaction_Bancaire 
                WHERE Transaction_ID = {issue.ligne_id}
                """
                results = self.oltp_conn.execute_query(query)
                
                if results:
                    compte_id = results[0][0]
                    date_transaction = results[0][1]
                    
                    # Set Date_Key
                    issue.date_key = self.get_date_key(date_transaction)
                    
                    # Set Transaction_Key from DW
                    issue.transaction_key = self.get_transaction_key_by_id(issue.ligne_id)
                    
                    # Get Compte_Key and related keys from DW via Compte
                    if compte_id:
                        compte_query = f"""
                        SELECT Numero_Compte, Client_ID 
                        FROM CoreBanking_OLTP.dbo.Compte 
                        WHERE Compte_ID = {compte_id}
                        """
                        compte_results = self.oltp_conn.execute_query(compte_query)
                        if compte_results:
                            numero_compte = compte_results[0][0]
                            client_id = compte_results[0][1]
                            
                            issue.compte_key = self.get_compte_key_by_numero(numero_compte)
                            
                            # Get Client_Key and Agence_Key via Client
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
    
    def get_transaction_key_by_id(self, transaction_id: int) -> int:
        """Get Transaction_Key from DW Dim_Transaction by matching transaction attributes"""
        try:
            # Get transaction details from OLTP
            query = f"""
            SELECT tb.Montant, tb.Date_Transaction, tb.Reference_Transaction, ct.Libelle AS Canal, tb.Type_Transaction
            FROM CoreBanking_OLTP.dbo.Transaction_Bancaire tb
            LEFT JOIN CoreBanking_OLTP.dbo.Canal_Transaction ct ON tb.Canal_ID = ct.Canal_ID
            WHERE tb.Transaction_ID = {transaction_id}
            """
            results = self.oltp_conn.execute_query(query)
            if results:
                row = results[0]
                montant = row[0]
                date_transaction = row[1]
                reference = row[2] if row[2] else ''
                canal = row[3] if row[3] else 'Standard'
                type_trans = row[4] if row[4] else 'Standard'
                
                # Match in DW using business attributes
                dw_query = f"""
                SELECT Transaction_Key 
                FROM CoreBanking_DW.dbo.Dim_Transaction 
                WHERE Montant = {montant} 
                AND Date_Transaction = '{date_transaction}'
                AND Reference = '{reference}'
                AND Canal = '{canal}'
                AND Type_Transaction = '{type_trans}'
                """
                dw_results = self.dwh_conn.execute_query(dw_query)
                if dw_results:
                    return dw_results[0][0]
            return None
        except Exception as e:
            logger.warning(f"Could not get Transaction_Key for ID {transaction_id}: {e}")
            return None


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
        
        engine = TransactionQualityEngine(oltp_conn, dwh_conn)
        results = engine.run_all_checks()
        
        print("\nTransaction Quality Check Results:")
        for check, count in results.items():
            print(f"  {check}: {count}")
        
    finally:
        oltp_conn.disconnect()
        dwh_conn.disconnect()
