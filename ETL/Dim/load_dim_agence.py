"""
ETL Process for Dim_Agence
Extracts data from OLTP.Agence and loads into DW.Dim_Agence
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ETL.db_connection import OLTPConnection, DWHConnection
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_agences(oltp_conn: OLTPConnection) -> list:
    """
    Extract agence data from OLTP database
    
    Args:
        oltp_conn: OLTP database connection
        
    Returns:
        List of tuples containing agence data
    """
    query = """
    SELECT 
        Code_Agence,
        Nom_Agence,
        Ville,
        Adresse,
        Telephone
    FROM CoreBanking_OLTP.dbo.Agence
    """
    
    try:
        results = oltp_conn.execute_query(query)
        logger.info(f"Extracted {len(results)} agences from OLTP")
        return results
    except Exception as e:
        logger.error(f"Error extracting agences: {e}")
        raise


def transform_agences(raw_data: list) -> list:
    """
    Transform agence data to match DW structure
    
    Args:
        raw_data: Raw data from OLTP
        
    Returns:
        Transformed data ready for DW
    """
    transformed = []
    
    for row in raw_data:
        transformed.append({
            'Code_Agence': row[0],
            'Nom_Agence': row[1],
            'Ville': row[2],
            'Adresse': row[3],
            'Telephone': row[4]
        })
    
    logger.info(f"Transformed {len(transformed)} agence records")
    return transformed


def load_dim_agence(dwh_conn: DWHConnection, transformed_data: list) -> dict:
    """
    Load transformed agence data into DW Dim_Agence table
    Performs UPDATE for existing agences and INSERT for new agences
    
    Args:
        dwh_conn: DWH database connection
        transformed_data: Transformed agence data
        
    Returns:
        Dictionary with counts of inserted and updated rows
    """
    if not transformed_data:
        logger.warning("No data to load")
        return {'inserted': 0, 'updated': 0}
    
    # Get existing agences from DW
    existing_agences_query = """
    SELECT Agence_Key, Code_Agence, Nom_Agence, Ville, Adresse, Telephone FROM CoreBanking_DW.dbo.Dim_Agence
    """
    existing_agences = {}
    
    try:
        existing_results = dwh_conn.execute_query(existing_agences_query)
        for row in existing_results:
            existing_agences[row[1]] = {
                'Agence_Key': row[0],
                'Code_Agence': row[1],
                'Nom_Agence': row[2],
                'Ville': row[3],
                'Adresse': row[4],
                'Telephone': row[5]
            }
        logger.info(f"Found {len(existing_agences)} existing agences in DW")
    except Exception as e:
        logger.warning(f"Could not fetch existing agences: {e}")
    
    # Separate new and existing agences
    new_agences = []
    existing_agences_data = []
    
    for agence in transformed_data:
        if agence['Code_Agence'] in existing_agences:
            agence['Agence_Key'] = existing_agences[agence['Code_Agence']]['Agence_Key']
            existing_agences_data.append(agence)
        else:
            new_agences.append(agence)
    
    rows_inserted = 0
    rows_updated = 0
    
    try:
        cursor = dwh_conn.connection.cursor()
        
        # Insert new agences
        if new_agences:
            insert_query = """
            INSERT INTO CoreBanking_DW.dbo.Dim_Agence 
            (Code_Agence, Nom_Agence, Ville, Adresse, Telephone)
            VALUES (?, ?, ?, ?, ?)
            """
            
            for agence in new_agences:
                cursor.execute(insert_query, (
                    agence['Code_Agence'],
                    agence['Nom_Agence'],
                    agence['Ville'],
                    agence['Adresse'],
                    agence['Telephone']
                ))
                rows_inserted += 1
            
            logger.info(f"Inserted {rows_inserted} new agences")
        
        # Update existing agences - only if values have changed
        if existing_agences_data:
            for agence in existing_agences_data:
                existing = existing_agences[agence['Code_Agence']]
                
                # Check if any column has changed
                columns_to_update = []
                update_values = []
                
                if str(agence['Nom_Agence']) != str(existing['Nom_Agence']):
                    columns_to_update.append('Nom_Agence = ?')
                    update_values.append(agence['Nom_Agence'])
                
                if str(agence['Ville']) != str(existing['Ville']):
                    columns_to_update.append('Ville = ?')
                    update_values.append(agence['Ville'])
                
                if str(agence['Adresse'] if agence['Adresse'] else '') != str(existing['Adresse'] if existing['Adresse'] else ''):
                    columns_to_update.append('Adresse = ?')
                    update_values.append(agence['Adresse'])
                
                if str(agence['Telephone'] if agence['Telephone'] else '') != str(existing['Telephone'] if existing['Telephone'] else ''):
                    columns_to_update.append('Telephone = ?')
                    update_values.append(agence['Telephone'])
                
                # Only execute UPDATE if at least one column changed
                if columns_to_update:
                    update_query = f"""
                    UPDATE CoreBanking_DW.dbo.Dim_Agence
                    SET {', '.join(columns_to_update)}
                    WHERE Agence_Key = ?
                    """
                    update_values.append(agence['Agence_Key'])
                    cursor.execute(update_query, tuple(update_values))
                    rows_updated += 1
            
            logger.info(f"Updated {rows_updated} existing agences")
        
        dwh_conn.connection.commit()
        cursor.close()
        
        logger.info(f"Load completed: {rows_inserted} inserted, {rows_updated} updated")
        return {'inserted': rows_inserted, 'updated': rows_updated}
        
    except Exception as e:
        logger.error(f"Error loading agences: {e}")
        dwh_conn.connection.rollback()
        raise


def run_dim_agence_etl(config: dict) -> dict:
    """
    Run complete ETL process for Dim_Agence
    
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
        
        raw_data = extract_agences(oltp_conn)
        result['extracted'] = len(raw_data)
        
        # Transform
        logger.info("Starting transformation...")
        transformed_data = transform_agences(raw_data)
        result['transformed'] = len(transformed_data)
        
        # Load
        logger.info("Starting load to DW...")
        dwh_conn = DWHConnection(config)
        if not dwh_conn.connect():
            raise Exception("Failed to connect to DWH database")
        
        load_results = load_dim_agence(dwh_conn, transformed_data)
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
    print("Starting Dim_Agence ETL process...")
    results = run_dim_agence_etl(config)
    
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
