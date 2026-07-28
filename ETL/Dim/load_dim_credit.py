"""
ETL Process for Dim_Credit
Extracts data from OLTP.Credit and loads into DW.Dim_Credit
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ETL.db_connection import OLTPConnection, DWHConnection
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_credits(oltp_conn: OLTPConnection) -> list:
    """
    Extract credit data from OLTP database
    
    Args:
        oltp_conn: OLTP database connection
        
    Returns:
        List of tuples containing credit data
    """
    query = """
    SELECT 
        Type_Credit,
        Montant,
        Duree_Mois,
        Taux_Interet,
        Date_Debut,
        Statut
    FROM CoreBanking_OLTP.dbo.Credit
    """
    
    try:
        results = oltp_conn.execute_query(query)
        logger.info(f"Extracted {len(results)} credits from OLTP")
        return results
    except Exception as e:
        logger.error(f"Error extracting credits: {e}")
        raise


def transform_credits(raw_data: list) -> list:
    """
    Transform credit data to match DW structure
    
    Args:
        raw_data: Raw data from OLTP
        
    Returns:
        Transformed data ready for DW
    """
    transformed = []
    
    for row in raw_data:
        transformed.append({
            'Type_Credit': row[0] if row[0] else 'Standard',
            'Montant': row[1] if row[1] is not None else 0.00,
            'Duree_Mois': row[2] if row[2] is not None else 0,
            'Taux_Interet': row[3] if row[3] is not None else 0.00,
            'Date_Debut': row[4],
            'Statut': row[5] if row[5] else 'En cours'
        })
    
    logger.info(f"Transformed {len(transformed)} credit records")
    return transformed


def load_dim_credit(dwh_conn: DWHConnection, transformed_data: list) -> dict:
    """
    Load transformed credit data into DW Dim_Credit table
    Performs UPDATE for existing credits and INSERT for new credits
    
    Args:
        dwh_conn: DWH database connection
        transformed_data: Transformed credit data
        
    Returns:
        Dictionary with counts of inserted and updated rows
    """
    if not transformed_data:
        logger.warning("No data to load")
        return {'inserted': 0, 'updated': 0}
    
    # Since Credit doesn't have a unique business key like CIN or Code_Agence,
    # we'll use a composite key for matching: Type_Credit + Montant + Date_Debut
    existing_credits_query = """
    SELECT Credit_Key, Type_Credit, Montant, Date_Debut FROM CoreBanking_DW.dbo.Dim_Credit
    """
    existing_credits = {}
    
    try:
        existing_results = dwh_conn.execute_query(existing_credits_query)
        for row in existing_results:
            composite_key = f"{row[1]}|{row[2]}|{row[3]}"
            existing_credits[composite_key] = row[0]
        logger.info(f"Found {len(existing_credits)} existing credits in DW")
    except Exception as e:
        logger.warning(f"Could not fetch existing credits: {e}")
    
    # Separate new and existing credits
    new_credits = []
    existing_credits_data = []
    
    for credit in transformed_data:
        composite_key = f"{credit['Type_Credit']}|{credit['Montant']}|{credit['Date_Debut']}"
        if composite_key in existing_credits:
            credit['Credit_Key'] = existing_credits[composite_key]
            existing_credits_data.append(credit)
        else:
            new_credits.append(credit)
    
    rows_inserted = 0
    rows_updated = 0
    
    try:
        cursor = dwh_conn.connection.cursor()
        
        # Insert new credits
        if new_credits:
            insert_query = """
            INSERT INTO CoreBanking_DW.dbo.Dim_Credit 
            (Type_Credit, Montant, Duree_Mois, Taux_Interet, Date_Debut, Statut)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            for credit in new_credits:
                cursor.execute(insert_query, (
                    credit['Type_Credit'],
                    credit['Montant'],
                    credit['Duree_Mois'],
                    credit['Taux_Interet'],
                    credit['Date_Debut'],
                    credit['Statut']
                ))
                rows_inserted += 1
            
            logger.info(f"Inserted {rows_inserted} new credits")
        
        # Update existing credits
        if existing_credits_data:
            update_query = """
            UPDATE CoreBanking_DW.dbo.Dim_Credit
            SET Montant = ?, Duree_Mois = ?, Taux_Interet = ?, Statut = ?
            WHERE Credit_Key = ?
            """
            
            for credit in existing_credits_data:
                cursor.execute(update_query, (
                    credit['Montant'],
                    credit['Duree_Mois'],
                    credit['Taux_Interet'],
                    credit['Statut'],
                    credit['Credit_Key']
                ))
                rows_updated += 1
            
            logger.info(f"Updated {rows_updated} existing credits")
        
        dwh_conn.connection.commit()
        cursor.close()
        
        logger.info(f"Load completed: {rows_inserted} inserted, {rows_updated} updated")
        return {'inserted': rows_inserted, 'updated': rows_updated}
        
    except Exception as e:
        logger.error(f"Error loading credits: {e}")
        dwh_conn.connection.rollback()
        raise


def run_dim_credit_etl(config: dict) -> dict:
    """
    Run complete ETL process for Dim_Credit
    
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
        
        raw_data = extract_credits(oltp_conn)
        result['extracted'] = len(raw_data)
        
        # Transform
        logger.info("Starting transformation...")
        transformed_data = transform_credits(raw_data)
        result['transformed'] = len(transformed_data)
        
        # Load
        logger.info("Starting load to DW...")
        dwh_conn = DWHConnection(config)
        if not dwh_conn.connect():
            raise Exception("Failed to connect to DWH database")
        
        load_results = load_dim_credit(dwh_conn, transformed_data)
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
    print("Starting Dim_Credit ETL process...")
    results = run_dim_credit_etl(config)
    
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
