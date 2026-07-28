"""
ETL Process for Fact_Accuracy
Loads data quality accuracy issues into DW.Fact_Accuracy table
Aggregates issues from all domain quality engines
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ETL.db_connection import DWHConnection, OLTPConnection
from ETL.DataQuality.dq_client import ClientQualityEngine
from ETL.DataQuality.dq_compte import CompteQualityEngine
from ETL.DataQuality.dq_transaction import TransactionQualityEngine
from ETL.DataQuality.dq_credit import CreditQualityEngine
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_fact_accuracy(dwh_conn: DWHConnection, issues: list) -> int:
    """
    Load quality issues into Fact_Accuracy table
    
    Args:
        dwh_conn: DWH database connection
        issues: List of QualityIssue objects
        
    Returns:
        Number of rows inserted
    """
    # Clear existing data to prevent duplication
    try:
        cursor = dwh_conn.connection.cursor()
        cursor.execute("DELETE FROM CoreBanking_DW.dbo.Fact_Accuracy")
        dwh_conn.connection.commit()
        cursor.close()
        logger.info("Cleared existing data from Fact_Accuracy")
    except Exception as e:
        logger.warning(f"Could not clear existing data: {e}")
    
    if not issues:
        logger.warning("No quality issues to load")
        return 0
    
    insert_query = """
    INSERT INTO CoreBanking_DW.dbo.Fact_Accuracy 
    (Date_Key, Client_Key, Agence_Key, Compte_Key, Transaction_Key, Credit_Key,
     Ligne_Id, Table_Name, Column_Name, Valeur_Erreur, Valeur_Attendue,
     Error_Message, Issue_Category, Severity, Business_Impact, Date_Detection)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
    """
    
    rows_inserted = 0
    try:
        cursor = dwh_conn.connection.cursor()
        
        for issue in issues:
            # Set dimension keys based on table name
            # For Transaction_Bancaire issues, use Transaction_Key
            # For Credit issues, use Credit_Key
            transaction_key_to_use = issue.transaction_key if issue.table_name == 'Transaction_Bancaire' else None
            credit_key_to_use = issue.credit_key if issue.table_name == 'Credit' else None
            
            cursor.execute(insert_query, (
                issue.date_key,
                issue.client_key,
                issue.agence_key,
                issue.compte_key,
                transaction_key_to_use,
                credit_key_to_use,
                issue.ligne_id,
                issue.table_name,
                issue.column_name,
                issue.valeur_erreur,
                issue.valeur_attendue,
                issue.error_message,
                issue.issue_category,
                issue.severity,
                issue.business_impact
            ))
            rows_inserted += 1
        
        dwh_conn.connection.commit()
        cursor.close()
        
        logger.info(f"Loaded {rows_inserted} quality issues into Fact_Accuracy")
        return rows_inserted
        
    except Exception as e:
        logger.error(f"Error loading quality issues: {e}")
        dwh_conn.connection.rollback()
        raise


def run_fact_accuracy_etl(config: dict) -> dict:
    """
    Run complete ETL process for Fact_Accuracy
    Runs all domain quality engines and loads detected issues
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Dictionary with ETL results
    """
    result = {
        'status': 'failed',
        'client_issues': 0,
        'compte_issues': 0,
        'transaction_issues': 0,
        'credit_issues': 0,
        'total_issues': 0,
        'loaded': 0,
        'error': None,
        'timestamp': datetime.now().isoformat()
    }
    
    oltp_conn = None
    dwh_conn = None
    
    try:
        # Connect to databases
        logger.info("Connecting to databases...")
        oltp_conn = OLTPConnection(config)
        if not oltp_conn.connect():
            raise Exception("Failed to connect to OLTP database")
        
        dwh_conn = DWHConnection(config)
        if not dwh_conn.connect():
            raise Exception("Failed to connect to DWH database")
        
        # Run all domain quality engines
        all_issues = []
        
        # Client domain
        logger.info("Running Client quality checks...")
        client_engine = ClientQualityEngine(oltp_conn, dwh_conn)
        client_results = client_engine.run_all_checks()
        result['client_issues'] = client_results['total_issues']
        all_issues.extend(client_engine.issues)
        
        # Compte domain
        logger.info("Running Compte quality checks...")
        compte_engine = CompteQualityEngine(oltp_conn, dwh_conn)
        compte_results = compte_engine.run_all_checks()
        result['compte_issues'] = compte_results['total_issues']
        all_issues.extend(compte_engine.issues)
        
        # Transaction domain
        logger.info("Running Transaction quality checks...")
        transaction_engine = TransactionQualityEngine(oltp_conn, dwh_conn)
        transaction_results = transaction_engine.run_all_checks()
        result['transaction_issues'] = transaction_results['total_issues']
        all_issues.extend(transaction_engine.issues)
        
        # Credit domain
        logger.info("Running Credit quality checks...")
        credit_engine = CreditQualityEngine(oltp_conn, dwh_conn)
        credit_results = credit_engine.run_all_checks()
        result['credit_issues'] = credit_results['total_issues']
        all_issues.extend(credit_engine.issues)
        
        result['total_issues'] = len(all_issues)
        
        # Load issues into Fact_Accuracy
        if all_issues:
            logger.info(f"Loading {len(all_issues)} quality issues into Fact_Accuracy...")
            loaded = load_fact_accuracy(dwh_conn, all_issues)
            result['loaded'] = loaded
        else:
            logger.info("No quality issues detected")
        
        result['status'] = 'success'
        logger.info("Fact_Accuracy ETL process completed successfully")
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Fact_Accuracy ETL process failed: {e}")
        
    finally:
        if oltp_conn:
            oltp_conn.disconnect()
        if dwh_conn:
            dwh_conn.disconnect()
    
    return result


if __name__ == "__main__":
    # Configuration
    config = {
        "dwh_server": "localhost",
        "dwh_database": "CoreBanking_DW",
        "oltp_server": "localhost",
        "oltp_database": "CoreBanking_OLTP",
        "trusted_connection": "yes",
        "username": "",
        "password": ""
    }
    
    # Run ETL
    print("Starting Fact_Accuracy ETL process...")
    results = run_fact_accuracy_etl(config)
    
    # Display results
    print("\nFact_Accuracy ETL Results:")
    print(f"  Status: {results['status']}")
    print(f"  Client Issues: {results['client_issues']}")
    print(f"  Compte Issues: {results['compte_issues']}")
    print(f"  Transaction Issues: {results['transaction_issues']}")
    print(f"  Credit Issues: {results['credit_issues']}")
    print(f"  Total Issues: {results['total_issues']}")
    print(f"  Loaded: {results['loaded']}")
    print(f"  Timestamp: {results['timestamp']}")
    
    if results['error']:
        print(f"  Error: {results['error']}")
