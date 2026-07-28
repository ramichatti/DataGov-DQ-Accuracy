"""
ETL Process for Dim_Compte
Extracts data from OLTP.Compte + OLTP.Type_Compte + OLTP.Devise and loads into DW.Dim_Compte
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ETL.db_connection import OLTPConnection, DWHConnection
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_comptes(oltp_conn: OLTPConnection) -> list:
    """
    Extract compte data from OLTP database
    
    Args:
        oltp_conn: OLTP database connection
        
    Returns:
        List of tuples containing compte data
    """
    query = """
    SELECT 
        c.Numero_Compte,
        tc.Libelle AS Type_Compte,
        d.Libelle AS Devise,
        c.Solde,
        c.Date_Ouverture,
        c.Statut
    FROM CoreBanking_OLTP.dbo.Compte c
    LEFT JOIN CoreBanking_OLTP.dbo.Type_Compte tc 
        ON c.Type_Compte_ID = tc.Type_Compte_ID
    LEFT JOIN CoreBanking_OLTP.dbo.Devise d 
        ON c.Devise_ID = d.Devise_ID
    """
    
    try:
        results = oltp_conn.execute_query(query)
        logger.info(f"Extracted {len(results)} comptes from OLTP")
        return results
    except Exception as e:
        logger.error(f"Error extracting comptes: {e}")
        raise


def transform_comptes(raw_data: list) -> list:
    """
    Transform compte data to match DW structure
    
    Args:
        raw_data: Raw data from OLTP
        
    Returns:
        Transformed data ready for DW
    """
    transformed = []
    
    for row in raw_data:
        transformed.append({
            'Numero_Compte': row[0],
            'Type_Compte': row[1] if row[1] else 'Standard',
            'Devise': row[2] if row[2] else 'TND',
            'Solde': row[3] if row[3] is not None else 0.00,
            'Date_Ouverture': row[4],
            'Statut': row[5] if row[5] else 'Actif'
        })
    
    logger.info(f"Transformed {len(transformed)} compte records")
    return transformed


def load_dim_compte(dwh_conn: DWHConnection, transformed_data: list) -> dict:
    """
    Load transformed compte data into DW Dim_Compte table
    Performs UPDATE for existing comptes and INSERT for new comptes
    
    Args:
        dwh_conn: DWH database connection
        transformed_data: Transformed compte data
        
    Returns:
        Dictionary with counts of inserted and updated rows
    """
    if not transformed_data:
        logger.warning("No data to load")
        return {'inserted': 0, 'updated': 0}
    
    # Get existing comptes from DW
    existing_comptes_query = """
    SELECT Compte_Key, Numero_Compte FROM CoreBanking_DW.dbo.Dim_Compte
    """
    existing_comptes = {}
    
    try:
        existing_results = dwh_conn.execute_query(existing_comptes_query)
        existing_comptes = {row[1]: row[0] for row in existing_results}
        logger.info(f"Found {len(existing_comptes)} existing comptes in DW")
    except Exception as e:
        logger.warning(f"Could not fetch existing comptes: {e}")
    
    # Separate new and existing comptes
    new_comptes = []
    existing_comptes_data = []
    
    for compte in transformed_data:
        if compte['Numero_Compte'] in existing_comptes:
            compte['Compte_Key'] = existing_comptes[compte['Numero_Compte']]
            existing_comptes_data.append(compte)
        else:
            new_comptes.append(compte)
    
    rows_inserted = 0
    rows_updated = 0
    
    try:
        cursor = dwh_conn.connection.cursor()
        
        # Insert new comptes
        if new_comptes:
            insert_query = """
            INSERT INTO CoreBanking_DW.dbo.Dim_Compte 
            (Numero_Compte, Type_Compte, Devise, Solde, Date_Ouverture, Statut)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            
            for compte in new_comptes:
                cursor.execute(insert_query, (
                    compte['Numero_Compte'],
                    compte['Type_Compte'],
                    compte['Devise'],
                    compte['Solde'],
                    compte['Date_Ouverture'],
                    compte['Statut']
                ))
                rows_inserted += 1
            
            logger.info(f"Inserted {rows_inserted} new comptes")
        
        # Update existing comptes
        if existing_comptes_data:
            update_query = """
            UPDATE CoreBanking_DW.dbo.Dim_Compte
            SET Type_Compte = ?, Devise = ?, Solde = ?, Date_Ouverture = ?, Statut = ?
            WHERE Compte_Key = ?
            """
            
            for compte in existing_comptes_data:
                cursor.execute(update_query, (
                    compte['Type_Compte'],
                    compte['Devise'],
                    compte['Solde'],
                    compte['Date_Ouverture'],
                    compte['Statut'],
                    compte['Compte_Key']
                ))
                rows_updated += 1
            
            logger.info(f"Updated {rows_updated} existing comptes")
        
        dwh_conn.connection.commit()
        cursor.close()
        
        logger.info(f"Load completed: {rows_inserted} inserted, {rows_updated} updated")
        return {'inserted': rows_inserted, 'updated': rows_updated}
        
    except Exception as e:
        logger.error(f"Error loading comptes: {e}")
        dwh_conn.connection.rollback()
        raise


def run_dim_compte_etl(config: dict) -> dict:
    """
    Run complete ETL process for Dim_Compte
    
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
        
        raw_data = extract_comptes(oltp_conn)
        result['extracted'] = len(raw_data)
        
        # Transform
        logger.info("Starting transformation...")
        transformed_data = transform_comptes(raw_data)
        result['transformed'] = len(transformed_data)
        
        # Load
        logger.info("Starting load to DW...")
        dwh_conn = DWHConnection(config)
        if not dwh_conn.connect():
            raise Exception("Failed to connect to DWH database")
        
        load_results = load_dim_compte(dwh_conn, transformed_data)
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
    print("Starting Dim_Compte ETL process...")
    results = run_dim_compte_etl(config)
    
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
