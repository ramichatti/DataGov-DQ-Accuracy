"""
Data Quality Engine for Client Domain
Performs accuracy checks on OLTP.Client table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataQuality.data_quality_engine import BaseQualityEngine, QualityIssue
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ClientQualityEngine(BaseQualityEngine):
    """Quality engine for Client domain accuracy checks"""
    
    def __init__(self, oltp_conn, dwh_conn):
        super().__init__(oltp_conn, dwh_conn)
    
    def run_all_checks(self) -> dict:
        """Run all accuracy checks for Client domain (Tunisia context)"""
        logger.info("Starting Client domain accuracy checks...")
        
        results = {
            'cin_format_tunisia': 0,
            'telephone_format_tunisia': 0,
            'email_format_accuracy': 0,
            'date_naissance_reasonable': 0,
            'total_issues': 0
        }
        
        # Accuracy Check 1: CIN format - Tunisian national ID (exactly 8 digits)
        query = """
        SELECT Client_ID, CIN 
        FROM CoreBanking_OLTP.dbo.Client 
        WHERE CIN IS NOT NULL 
        AND (LEN(CIN) <> 8 OR ISNUMERIC(CIN) = 0)
        """
        results['cin_format_tunisia'] = self.check_accuracy_validation(
            'Client', 'CIN', query, '8 digits (Tunisian format)', 'High',
            'CIN must be exactly 8 digits for Tunisian national ID'
        )
        
        # Accuracy Check 2: Telephone format - Tunisian phone numbers (+216 or 00216 + 8 digits)
        query = """
        SELECT Client_ID, Telephone 
        FROM CoreBanking_OLTP.dbo.Client 
        WHERE Telephone IS NOT NULL AND Telephone <> ''
        AND NOT (
            REPLACE(REPLACE(REPLACE(Telephone, '+', ''), ' ', ''), '-', '') LIKE '216%'
            AND LEN(REPLACE(REPLACE(REPLACE(Telephone, '+', ''), ' ', ''), '-', '')) = 11
        )
        """
        results['telephone_format_tunisia'] = self.check_accuracy_validation(
            'Client', 'Telephone', query, '+216 or 00216 followed by 8 digits', 'High',
            'Tunisian phone numbers must start with +216 or 00216 followed by 8 digits'
        )
        
        # Accuracy Check 3: Email format accuracy
        query = """
        SELECT Client_ID, Email 
        FROM CoreBanking_OLTP.dbo.Client 
        WHERE Email IS NOT NULL AND Email <> '' 
        AND Email NOT LIKE '%_@__%.__%'
        """
        results['email_format_accuracy'] = self.check_accuracy_validation(
            'Client', 'Email', query, 'Valid email format (user@domain.extension)', 'Medium',
            'Email must follow standard format with @ and domain extension'
        )
        
        # Accuracy Check 4: Date_Naissance reasonable (not in future, not before 1900, not too young)
        query = """
        SELECT Client_ID, Date_Naissance 
        FROM CoreBanking_OLTP.dbo.Client 
        WHERE Date_Naissance IS NOT NULL 
        AND (Date_Naissance > GETDATE() OR Date_Naissance < '1900-01-01' OR DATEDIFF(YEAR, Date_Naissance, GETDATE()) < 18)
        """
        results['date_naissance_reasonable'] = self.check_accuracy_validation(
            'Client', 'Date_Naissance', query, 'Between 1900-01-01 and 18 years ago', 'High',
            'Birth date must be reasonable (not in future, not before 1900, client must be 18+)'
        )
        
        # Enrich issues with dimension keys
        self.enrich_issues_with_dimension_keys()
        
        results['total_issues'] = self.get_issues_count()
        logger.info(f"Client quality checks completed. Total issues: {results['total_issues']}")
        
        return results
    
    def enrich_issues_with_dimension_keys(self):
        """Enrich quality issues with dimension keys from DW"""
        for issue in self.issues:
            try:
                # Get client info from OLTP to find dimension keys
                query = f"""
                SELECT CIN, Agence_ID 
                FROM CoreBanking_OLTP.dbo.Client 
                WHERE Client_ID = {issue.ligne_id}
                """
                results = self.oltp_conn.execute_query(query)
                
                if results:
                    cin = results[0][0]
                    agence_id = results[0][1]
                    
                    # Get Client_Key from DW
                    issue.client_key = self.get_client_key_by_cin(cin)
                    
                    # Get Agence_Key from DW (need to get code from OLTP first)
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
        
        engine = ClientQualityEngine(oltp_conn, dwh_conn)
        results = engine.run_all_checks()
        
        print("\nClient Quality Check Results:")
        for check, count in results.items():
            print(f"  {check}: {count}")
        
    finally:
        oltp_conn.disconnect()
        dwh_conn.disconnect()
