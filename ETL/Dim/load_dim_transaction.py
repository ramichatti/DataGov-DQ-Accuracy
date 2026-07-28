"""
ETL Process for Dim_Transaction
Extracts data from OLTP.Transaction_Bancaire + OLTP.Canal_Transaction and loads into DW.Dim_Transaction
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ETL.db_connection import OLTPConnection, DWHConnection
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_transactions(oltp_conn: OLTPConnection) -> list:
    """
    Extract transaction data from OLTP database
    
    Args:
        oltp_conn: OLTP database connection
        
    Returns:
        List of tuples containing transaction data
    """
    query = """
    SELECT 
        tb.Transaction_ID,
        ct.Libelle AS Canal,
        tb.Type_Transaction,
        tb.Montant,
        tb.Date_Transaction,
        tb.Reference_Transaction
    FROM CoreBanking_OLTP.dbo.Transaction_Bancaire tb
    LEFT JOIN CoreBanking_OLTP.dbo.Canal_Transaction ct 
        ON tb.Canal_ID = ct.Canal_ID
    """
    
    try:
        results = oltp_conn.execute_query(query)
        logger.info(f"Extracted {len(results)} transactions from OLTP")
        return results
    except Exception as e:
        logger.error(f"Error extracting transactions: {e}")
        raise


def transform_transactions(raw_data: list) -> list:
    """
    Transform transaction data to match DW structure
    
    Args:
        raw_data: Raw data from OLTP
        
    Returns:
        Transformed data ready for DW
    """
    transformed = []
    
    for row in raw_data:
        transformed.append({
            'Transaction_ID_Source': row[0],
            'Canal': row[1] if row[1] else 'Standard',
            'Type_Transaction': row[2] if row[2] else 'Standard',
            'Montant': row[3] if row[3] is not None else 0.00,
            'Date_Transaction': row[4],
            'Reference': row[5] if row[5] else ''
        })
    
    logger.info(f"Transformed {len(transformed)} transaction records")
    return transformed


def load_dim_transaction(dwh_conn: DWHConnection, transformed_data: list) -> dict:
    """
    Load transformed transaction data into DW Dim_Transaction table
    Performs UPDATE for existing transactions and INSERT for new transactions
    
    Args:
        dwh_conn: DWH database connection
        transformed_data: Transformed transaction data
        
    Returns:
        Dictionary with counts of inserted and updated rows
    """
    if not transformed_data:
        logger.warning("No data to load")
        return {'inserted': 0, 'updated': 0}
    
    # Get existing transactions from DW using Transaction_ID_Source (stable business key)
    existing_transactions_query = """
    SELECT Transaction_Key, Transaction_ID_Source, Canal, Type_Transaction, Montant, Date_Transaction, Reference 
    FROM CoreBanking_DW.dbo.Dim_Transaction
    """
    existing_transactions = {}
    
    try:
        existing_results = dwh_conn.execute_query(existing_transactions_query)
        for row in existing_results:
            if row[1] is not None:
                existing_transactions[row[1]] = {
                    'Transaction_Key': row[0],
                    'Transaction_ID_Source': row[1],
                    'Canal': row[2],
                    'Type_Transaction': row[3],
                    'Montant': row[4],
                    'Date_Transaction': row[5],
                    'Reference': row[6]
                }
        logger.info(f"Found {len(existing_transactions)} existing transactions in DW")
    except Exception as e:
        logger.warning(f"Could not fetch existing transactions: {e}")
    
    new_transactions = []
    existing_transactions_data = []
    
    for transaction in transformed_data:
        transaction_id = transaction['Transaction_ID_Source']
        if transaction_id in existing_transactions:
            transaction['Transaction_Key'] = existing_transactions[transaction_id]['Transaction_Key']
            existing_transactions_data.append(transaction)
        else:
            new_transactions.append(transaction)
    
    rows_inserted = 0
    rows_updated = 0
    
    try:
        cursor = dwh_conn.connection.cursor()
        
        # Insert new transactions
        if new_transactions:
            insert_query = """
            INSERT INTO CoreBanking_DW.dbo.Dim_Transaction 
            (Transaction_ID_Source, Canal, Type_Transaction, Montant, Date_Transaction, Reference)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            for transaction in new_transactions:
                cursor.execute(insert_query, (
                    transaction['Transaction_ID_Source'],
                    transaction['Canal'],
                    transaction['Type_Transaction'],
                    transaction['Montant'],
                    transaction['Date_Transaction'],
                    transaction['Reference']
                ))
                rows_inserted += 1
            
            logger.info(f"Inserted {rows_inserted} new transactions")
        
        # Update existing transactions - only if values have changed
        if existing_transactions_data:
            for transaction in existing_transactions_data:
                existing = existing_transactions[transaction['Transaction_ID_Source']]
                
                columns_to_update = []
                update_values = []
                
                if str(transaction['Canal']) != str(existing['Canal']):
                    columns_to_update.append('Canal = ?')
                    update_values.append(transaction['Canal'])
                
                if str(transaction['Type_Transaction']) != str(existing['Type_Transaction']):
                    columns_to_update.append('Type_Transaction = ?')
                    update_values.append(transaction['Type_Transaction'])
                
                if str(transaction['Montant']) != str(existing['Montant']):
                    columns_to_update.append('Montant = ?')
                    update_values.append(transaction['Montant'])
                
                if str(transaction['Date_Transaction']) != str(existing['Date_Transaction']):
                    columns_to_update.append('Date_Transaction = ?')
                    update_values.append(transaction['Date_Transaction'])
                
                if str(transaction['Reference'] if transaction['Reference'] else '') != str(existing['Reference'] if existing['Reference'] else ''):
                    columns_to_update.append('Reference = ?')
                    update_values.append(transaction['Reference'])
                
                # Only execute UPDATE if at least one column changed
                if columns_to_update:
                    update_query = f"""
                    UPDATE CoreBanking_DW.dbo.Dim_Transaction
                    SET {', '.join(columns_to_update)}
                    WHERE Transaction_Key = ?
                    """
                    update_values.append(transaction['Transaction_Key'])
                    cursor.execute(update_query, tuple(update_values))
                    rows_updated += 1
            
            logger.info(f"Updated {rows_updated} existing transactions")
        
        dwh_conn.connection.commit()
        cursor.close()
        
        logger.info(f"Load completed: {rows_inserted} inserted, {rows_updated} updated")
        return {'inserted': rows_inserted, 'updated': rows_updated}
        
    except Exception as e:
        logger.error(f"Error loading transactions: {e}")
        dwh_conn.connection.rollback()
        raise


def run_dim_transaction_etl(config: dict) -> dict:
    """
    Run complete ETL process for Dim_Transaction
    
    Args:
        config: Database configuration dictionary
        
    Returns:
        Dictionary with ETL results
    """
    result = {
        'status': 'failed',
        'extracted': 0,
        'transformed': 0,
        'inserted': 0,
        'updated': 0,
        'error': None,
        'timestamp': datetime.now().isoformat()
    }
    
    oltp_conn = None
    dwh_conn = None
    
    try:
        # Extract
        logger.info("Starting extraction from OLTP...")
        oltp_conn = OLTPConnection(config)
        if not oltp_conn.connect():
            raise Exception("Failed to connect to OLTP database")
        
        raw_data = extract_transactions(oltp_conn)
        result['extracted'] = len(raw_data)
        
        # Transform
        logger.info("Starting transformation...")
        transformed_data = transform_transactions(raw_data)
        result['transformed'] = len(transformed_data)
        
        # Load
        logger.info("Starting load to DW...")
        dwh_conn = DWHConnection(config)
        if not dwh_conn.connect():
            raise Exception("Failed to connect to DWH database")
        
        load_results = load_dim_transaction(dwh_conn, transformed_data)
        result['inserted'] = load_results['inserted']
        result['updated'] = load_results['updated']
        
        result['status'] = 'success'
        logger.info("ETL process completed successfully")
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"ETL process failed: {e}")
        
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
    print("Starting Dim_Transaction ETL process...")
    results = run_dim_transaction_etl(config)
    
    # Display results
    print("\nETL Results:")
    print(f"  Status: {results['status']}")
    print(f"  Extracted: {results['extracted']}")
    print(f"  Transformed: {results['transformed']}")
    print(f"  Inserted: {results['inserted']}")
    print(f"  Updated: {results['updated']}")
    print(f"  Timestamp: {results['timestamp']}")
    
    if results['error']:
        print(f"  Error: {results['error']}")
