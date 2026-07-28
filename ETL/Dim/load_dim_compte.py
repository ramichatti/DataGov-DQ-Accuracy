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
        c.Compte_ID,
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
            'Compte_ID_Source': row[0],
            'Numero_Compte': row[1],
            'Type_Compte': row[2] if row[2] else 'Standard',
            'Devise': row[3] if row[3] else 'TND',
            'Solde': row[4] if row[4] is not None else 0.00,
            'Date_Ouverture': row[5],
            'Statut': row[6] if row[6] else 'Actif'
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
    
    # Get existing comptes from DW using Compte_ID_Source (stable business key)
    existing_comptes_query = """
    SELECT Compte_Key, Compte_ID_Source, Numero_Compte, Type_Compte, Devise, Solde, Date_Ouverture, Statut FROM CoreBanking_DW.dbo.Dim_Compte
    """
    existing_comptes = {}
    
    try:
        existing_results = dwh_conn.execute_query(existing_comptes_query)
        for row in existing_results:
            if row[1] is not None:
                existing_comptes[row[1]] = {
                    'Compte_Key': row[0],
                    'Compte_ID_Source': row[1],
                    'Numero_Compte': row[2],
                    'Type_Compte': row[3],
                    'Devise': row[4],
                    'Solde': row[5],
                    'Date_Ouverture': row[6],
                    'Statut': row[7]
                }
        logger.info(f"Found {len(existing_comptes)} existing comptes in DW")
    except Exception as e:
        logger.warning(f"Could not fetch existing comptes: {e}")
    
    new_comptes = []
    existing_comptes_data = []
    
    for compte in transformed_data:
        compte_id = compte['Compte_ID_Source']
        if compte_id in existing_comptes:
            compte['Compte_Key'] = existing_comptes[compte_id]['Compte_Key']
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
            (Compte_ID_Source, Numero_Compte, Type_Compte, Devise, Solde, Date_Ouverture, Statut)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            
            for compte in new_comptes:
                cursor.execute(insert_query, (
                    compte['Compte_ID_Source'],
                    compte['Numero_Compte'],
                    compte['Type_Compte'],
                    compte['Devise'],
                    compte['Solde'],
                    compte['Date_Ouverture'],
                    compte['Statut']
                ))
                rows_inserted += 1
            
            logger.info(f"Inserted {rows_inserted} new comptes")
        
        # Update existing comptes - only if values have changed
        if existing_comptes_data:
            for compte in existing_comptes_data:
                existing = existing_comptes[compte['Compte_ID_Source']]
                
                # Check if any column has changed
                columns_to_update = []
                update_values = []
                
                if str(compte['Type_Compte']) != str(existing['Type_Compte']):
                    columns_to_update.append('Type_Compte = ?')
                    update_values.append(compte['Type_Compte'])
                
                if str(compte['Devise']) != str(existing['Devise']):
                    columns_to_update.append('Devise = ?')
                    update_values.append(compte['Devise'])
                
                if str(compte['Solde']) != str(existing['Solde']):
                    columns_to_update.append('Solde = ?')
                    update_values.append(compte['Solde'])
                
                if str(compte['Date_Ouverture']) != str(existing['Date_Ouverture']):
                    columns_to_update.append('Date_Ouverture = ?')
                    update_values.append(compte['Date_Ouverture'])
                
                if str(compte['Statut']) != str(existing['Statut']):
                    columns_to_update.append('Statut = ?')
                    update_values.append(compte['Statut'])
                
                # Only execute UPDATE if at least one column changed
                if columns_to_update:
                    update_query = f"""
                    UPDATE CoreBanking_DW.dbo.Dim_Compte
                    SET {', '.join(columns_to_update)}
                    WHERE Compte_Key = ?
                    """
                    update_values.append(compte['Compte_Key'])
                    cursor.execute(update_query, tuple(update_values))
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
