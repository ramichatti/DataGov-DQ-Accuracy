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
        va_lower = valeur_attendue.lower()
        
        # CIN validation: only for column_name == 'CIN'
        if column_name == 'CIN' and '8 digit' in va_lower:
            return not (len(current_str) == 8 and current_str.isdigit())
        
        # Telephone validation: "+216 or 00216 followed by 8 digits"
        if column_name == 'Telephone' and ('+216' in valeur_attendue or '00216' in valeur_attendue):
            cleaned = current_str.replace('+', '').replace(' ', '').replace('-', '')
            is_valid = cleaned.startswith('216') and len(cleaned) == 11
            return not is_valid
        
        # Email validation: "Valid email format"
        if column_name == 'Email' and 'email' in va_lower and '@' in valeur_attendue:
            import re
            is_valid = bool(re.match(r'[^@]+@[^@]+\.[^@]+', current_str))
            return not is_valid
        
        # Business logic: re-check the original condition
        # "Closed accounts should have zero balance" -> Compte.Statut, check Statut AND Solde
        if 'should' in va_lower or 'must' in va_lower:
            if table_name == 'Compte' and column_name == 'Statut' and 'zero' in va_lower:
                row_query = f"SELECT Statut, Solde FROM CoreBanking_OLTP.dbo.Compte WHERE Compte_ID = {ligne_id}"
                row_results = oltp_conn.execute_query(row_query)
                if row_results:
                    still_bad = row_results[0][0] == 'Cloture' and (row_results[0][1] or 0) != 0
                    return still_bad
            # Company-type clients must be 18+ -> Client.Date_Naissance
            if table_name == 'Client' and column_name == 'Date_Naissance' and '18' in va_lower:
                row_query = f"SELECT Date_Naissance, Type_Client_ID FROM CoreBanking_OLTP.dbo.Client WHERE Client_ID = {ligne_id}"
                row_results = oltp_conn.execute_query(row_query)
                if row_results and row_results[0][0]:
                    from datetime import date
                    age = date.today().year - row_results[0][0].year
                    still_bad = age < 18
                    return still_bad
                return True
            # Virement transactions must have positive amount
            if table_name == 'Transaction_Bancaire' and column_name == 'Montant' and 'positive' in va_lower:
                return float(current_value) <= 0
            # Monthly payment should be at least 10 -> Credit.Montant
            if table_name == 'Credit' and column_name == 'Montant' and 'monthly' in va_lower:
                row_query = f"SELECT Montant, Duree_Mois FROM CoreBanking_OLTP.dbo.Credit WHERE Credit_ID = {ligne_id}"
                row_results = oltp_conn.execute_query(row_query)
                if row_results and row_results[0][1]:
                    return (row_results[0][0] or 0) / row_results[0][1] < 10
            return True
        
        # Range validation: "Between X and Y" (dates or numbers)
        if 'between' in va_lower and 'and' in va_lower:
            import re
            from datetime import datetime, date
            
            # Try date first: check if current value looks like a date
            date_val = None
            try:
                date_val = datetime.strptime(current_str[:10], '%Y-%m-%d')
            except:
                pass
            
            if date_val:
                # Parse min/max dates from valeur_attendue
                date_parts = re.findall(r'\d{4}-\d{2}-\d{2}', valeur_attendue)
                if len(date_parts) >= 2:
                    min_date = datetime.strptime(date_parts[0], '%Y-%m-%d')
                    max_date = datetime.strptime(date_parts[1], '%Y-%m-%d')
                    return not (min_date <= date_val <= max_date)
                elif len(date_parts) == 1:
                    # Only min date found (e.g. "Between 1900-01-01 and 18 years ago")
                    min_date = datetime.strptime(date_parts[0], '%Y-%m-%d')
                    # Check if value is reasonable (not before min, not future, person >= 18)
                    if '18' in va_lower and ('year' in va_lower or 'age' in va_lower):
                        today = datetime.combine(date.today(), datetime.min.time())
                        min_age_date = datetime(today.year - 18, today.month, today.day)
                        return not (min_date <= date_val <= min_age_date)
                    elif 'current date' in va_lower or 'today' in va_lower:
                        today = datetime.combine(date.today(), datetime.min.time())
                        return not (min_date <= date_val <= today)
                    return True
            
            # Numeric range: extract numbers with B/M suffixes
            import math
            nums = re.findall(r"[\d.]+", valeur_attendue)
            if len(nums) >= 2:
                # Find actual positions in original string to detect suffixes
                min_str = nums[0]
                max_str = nums[1]
                
                min_idx = valeur_attendue.find(min_str)
                max_idx = valeur_attendue.find(max_str, min_idx + len(min_str))
                
                min_val = float(min_str)
                max_val = float(max_str)
                
                # Check for negative sign before min
                if min_idx > 0 and valeur_attendue[min_idx-1] == '-':
                    min_val = -min_val
                
                # Check for B/M suffix after min
                after_min = valeur_attendue[min_idx + len(min_str):min_idx + len(min_str) + 1]
                if after_min == 'B':
                    min_val *= 1000000000
                elif after_min == 'M':
                    min_val *= 1000000
                
                # Check for B/M suffix after max
                after_max = valeur_attendue[max_idx + len(max_str):max_idx + len(max_str) + 1]
                if after_max == 'B':
                    max_val *= 1000000000
                elif after_max == 'M':
                    max_val *= 1000000
                
                curr_val = float(current_value)
                return not (min_val <= curr_val <= max_val)
            return True
        
        # Default: assume issue persists
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
    
    # Load existing unsolved issues keyed by (Table_Name, Column_Name, Ligne_Id, Error_Message)
    # On duplicate: update Date_Detection; keep Solved/date_de_resolution unchanged (resolution only)
    existing_query = """
    SELECT Accuracy_Key, Table_Name, Column_Name, Ligne_Id, Error_Message
    FROM CoreBanking_DW.dbo.Fact_Accuracy WHERE Solved = 0
    """
    existing_map = {}
    try:
        cursor = dwh_conn.connection.cursor()
        cursor.execute(existing_query)
        for row in cursor.fetchall():
            existing_map[(str(row[1]), str(row[2]), int(row[3]), str(row[4] or ''))] = int(row[0])
        cursor.close()
    except Exception:
        existing_map = {}
    
    rows_inserted = 0
    rows_updated = 0
    seen_in_batch = set()
    
    insert_query = """
    INSERT INTO CoreBanking_DW.dbo.Fact_Accuracy 
    (Date_Key, Client_Key, Agence_Key, Compte_Key, Transaction_Key, Credit_Key,
     Ligne_Id, Table_Name, Column_Name, Valeur_Erreur, Valeur_Attendue,
     Error_Message, Severity, Date_Detection, Solved, date_de_resolution)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 0, NULL)
    """
    
    update_query = """
    UPDATE CoreBanking_DW.dbo.Fact_Accuracy
    SET Date_Detection = GETDATE()
    WHERE Accuracy_Key = ?
    """
    
    try:
        cursor = dwh_conn.connection.cursor()
        
        for issue in issues:
            key = (issue.table_name, issue.column_name, issue.ligne_id, issue.error_message)
            if key in existing_map:
                cursor.execute(update_query, (existing_map[key],))
                rows_updated += 1
            elif key not in seen_in_batch:
                seen_in_batch.add(key)
                compte_key_to_use = issue.compte_key if issue.table_name in ['Compte', 'Transaction_Bancaire'] else None
                transaction_key_to_use = issue.transaction_key if issue.table_name == 'Transaction_Bancaire' else None
                credit_key_to_use = issue.credit_key if issue.table_name == 'Credit' else None
                cursor.execute(insert_query, (
                    issue.date_key, issue.client_key, issue.agence_key,
                    compte_key_to_use, transaction_key_to_use, credit_key_to_use,
                    issue.ligne_id, issue.table_name, issue.column_name,
                    issue.valeur_erreur, issue.valeur_attendue,
                    issue.error_message, issue.severity
                ))
                rows_inserted += 1
        
        dwh_conn.connection.commit()
        cursor.close()
        
        if rows_updated > 0:
            logger.info(f"Updated Date_Detection for {rows_updated} existing issues")
        if rows_inserted > 0:
            logger.info(f"Loaded {rows_inserted} new quality issues into Fact_Accuracy")
        else:
            logger.info("No new quality issues to insert (all already tracked)")
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
        
        # Load issues into Fact_Accuracy (always call to resolve old issues too)
        if all_issues:
            logger.info(f"Loading {len(all_issues)} quality issues into Fact_Accuracy...")
        load_results = load_fact_accuracy(dwh_conn, oltp_conn, all_issues)
        result['loaded'] = load_results['inserted']
        result['resolved'] = load_results['resolved']
        
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
