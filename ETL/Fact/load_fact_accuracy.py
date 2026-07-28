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


def check_issue_still_exists(oltp_conn: OLTPConnection, table_name: str, column_name: str, ligne_id: int, valeur_attendue: str = '') -> bool:
    """
    Check if an issue still exists in OLTP data
    Validates the current column value against the expected format
    
    Args:
        oltp_conn: OLTP database connection
        table_name: Name of the table
        column_name: Name of the column
        ligne_id: ID of the row
        valeur_attendue: Expected format description
        
    Returns:
        True if issue still exists, False if resolved
    """
    try:
        pk_columns = {
            'Client': 'Client_ID',
            'Compte': 'Compte_ID',
            'Transaction_Bancaire': 'Transaction_ID',
            'Credit': 'Credit_ID'
        }
        
        pk_column = pk_columns.get(table_name, 'ID')
        
        query = f"SELECT {column_name} FROM CoreBanking_OLTP.dbo.{table_name} WHERE {pk_column} = {ligne_id}"
        results = oltp_conn.execute_query(query)
        
        if not results:
            return False
        
        current_value = results[0][0]
        if current_value is None:
            return True
        
        current_str = str(current_value)
        
        # CIN validation: "8 digits (Tunisian format)"
        if '8 digit' in valeur_attendue.lower():
            return not (len(current_str) == 8 and current_str.isdigit())
        
        # Telephone validation: "+216 or 00216 followed by 8 digits"
        if '+216' in valeur_attendue or '00216' in valeur_attendue:
            cleaned = current_str.replace('+', '').replace(' ', '').replace('-', '')
            is_valid = cleaned.startswith('216') and len(cleaned) == 11
            return not is_valid
        
        # Email validation: "Valid email format"
        if 'email' in valeur_attendue.lower() and '@' in valeur_attendue:
            import re
            is_valid = bool(re.match(r'[^@]+@[^@]+\.[^@]+', current_str))
            return not is_valid
        
        # Date validation: "Between X and Y" or "Between Y and Z"
        if 'between' in valeur_attendue.lower() and 'and' in valeur_attendue.lower():
            try:
                from datetime import datetime
                date_val = datetime.strptime(current_str[:10], '%Y-%m-%d') if len(current_str) >= 10 else None
                if date_val:
                    import re
                    parts = re.findall(r"[\d-]+", valeur_attendue)
                    min_date = datetime.strptime(parts[0], '%Y-%m-%d') if len(parts) > 0 else None
                    max_date = datetime.strptime(parts[1], '%Y-%m-%d') if len(parts) > 1 else None
                    if min_date and max_date:
                        return not (min_date <= date_val <= max_date)
            except:
                pass
            return True
        
        # Range validation for numbers: "Between X and Y"
        if 'between' in valeur_attendue.lower() and 'and' in valeur_attendue.lower():
            try:
                import re
                nums = re.findall(r"[\d.]+", valeur_attendue)
                if len(nums) >= 2:
                    min_val = float(nums[0])
                    max_val = float(nums[1])
                    curr_val = float(current_value)
                    return not (min_val <= curr_val <= max_val)
            except:
                pass
            return True
        
        # Business logic: "Closed accounts should have zero balance" etc.
        # For these, we re-check the original condition by querying the row
        if 'should' in valeur_attendue.lower() or 'must' in valeur_attendue.lower():
            return True
        
        # Default: if row exists, check if value is still null (for null checks)
        # or assume issue persists
        return True
        
    except Exception as e:
        logger.warning(f"Error checking if issue exists: {e}")
        return True


def update_resolved_issues(dwh_conn: DWHConnection, oltp_conn: OLTPConnection) -> int:
    """
    Check existing unsolved issues and mark as resolved if they no longer exist in OLTP
    
    Args:
        dwh_conn: DWH database connection
        oltp_conn: OLTP database connection
        
    Returns:
        Number of issues marked as resolved
    """
    try:
        # Get all unsolved issues
        query = """
        SELECT Accuracy_Key, Table_Name, Column_Name, Ligne_Id, Valeur_Attendue 
        FROM CoreBanking_DW.dbo.Fact_Accuracy 
        WHERE Solved = 0
        """
        cursor = dwh_conn.connection.cursor()
        cursor.execute(query)
        unsolved_issues = cursor.fetchall()
        cursor.close()
        
        resolved_count = 0
        current_time = datetime.now()
        
        for issue in unsolved_issues:
            accuracy_key = issue[0]
            table_name = issue[1]
            column_name = issue[2]
            ligne_id = issue[3]
            valeur_attendue = issue[4] if len(issue) > 4 and issue[4] else ''
            
            # Check if issue still exists in OLTP
            still_exists = check_issue_still_exists(oltp_conn, table_name, column_name, ligne_id, valeur_attendue)
            
            if not still_exists:
                # Mark as resolved
                cursor = dwh_conn.connection.cursor()
                update_query = """
                UPDATE CoreBanking_DW.dbo.Fact_Accuracy 
                SET Solved = 1, date_de_resolution = ? 
                WHERE Accuracy_Key = ?
                """
                cursor.execute(update_query, (current_time, accuracy_key))
                dwh_conn.connection.commit()
                cursor.close()
                resolved_count += 1
                logger.info(f"Marked issue {accuracy_key} as resolved")
        
        if resolved_count > 0:
            logger.info(f"Resolved {resolved_count} issues")
        
        return resolved_count
        
    except Exception as e:
        logger.error(f"Error updating resolved issues: {e}")
        return 0


def load_fact_accuracy(dwh_conn: DWHConnection, oltp_conn: OLTPConnection, issues: list) -> dict:
    """
    Load quality issues into Fact_Accuracy table
    Also checks for resolved issues and updates them
    
    Args:
        dwh_conn: DWH database connection
        oltp_conn: OLTP database connection
        issues: List of QualityIssue objects
        
    Returns:
        Dictionary with counts of inserted and resolved issues
    """
    result = {
        'inserted': 0,
        'resolved': 0
    }
    
    # First, check for resolved issues
    logger.info("Checking for resolved issues...")
    resolved_count = update_resolved_issues(dwh_conn, oltp_conn)
    result['resolved'] = resolved_count
    
    if not issues:
        logger.warning("No quality issues to load")
        return result
    
    insert_query = """
    INSERT INTO CoreBanking_DW.dbo.Fact_Accuracy 
    (Date_Key, Client_Key, Agence_Key, Compte_Key, Transaction_Key, Credit_Key,
     Ligne_Id, Table_Name, Column_Name, Valeur_Erreur, Valeur_Attendue,
     Error_Message, Severity, Date_Detection, Solved, date_de_resolution)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), ?, ?)
    """
    
    rows_inserted = 0
    try:
        cursor = dwh_conn.connection.cursor()
        
        for issue in issues:
            # Set dimension keys based on table name and enriched data
            # All issues should have client_key and agence_key from enrichment
            # Compte issues should have compte_key
            # Transaction_Bancaire issues should have transaction_key
            # Credit issues should have credit_key
            
            compte_key_to_use = issue.compte_key if issue.table_name in ['Compte', 'Transaction_Bancaire'] else None
            transaction_key_to_use = issue.transaction_key if issue.table_name == 'Transaction_Bancaire' else None
            credit_key_to_use = issue.credit_key if issue.table_name == 'Credit' else None
            
            cursor.execute(insert_query, (
                issue.date_key,
                issue.client_key,
                issue.agence_key,
                compte_key_to_use,
                transaction_key_to_use,
                credit_key_to_use,
                issue.ligne_id,
                issue.table_name,
                issue.column_name,
                issue.valeur_erreur,
                issue.valeur_attendue,
                issue.error_message,
                issue.severity,
                issue.solved,
                issue.date_de_resolution
            ))
            rows_inserted += 1
        
        dwh_conn.connection.commit()
        cursor.close()
        
        logger.info(f"Loaded {rows_inserted} quality issues into Fact_Accuracy")
        result['inserted'] = rows_inserted
        return result
        
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
        'resolved': 0,
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
            load_results = load_fact_accuracy(dwh_conn, oltp_conn, all_issues)
            result['loaded'] = load_results['inserted']
            result['resolved'] = load_results['resolved']
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
    print(f"  Resolved: {results['resolved']}")
    print(f"  Timestamp: {results['timestamp']}")
    
    if results['error']:
        print(f"  Error: {results['error']}")
