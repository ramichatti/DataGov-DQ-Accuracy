"""
ETL Process for Dim_Client
Extracts data from OLTP.Client + OLTP.Type_Client and loads into DW.Dim_Client
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ETL.db_connection import OLTPConnection, DWHConnection
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def extract_clients(oltp_conn: OLTPConnection) -> list:
    """
    Extract client data from OLTP database
    
    Args:
        oltp_conn: OLTP database connection
        
    Returns:
        List of tuples containing client data
    """
    query = """
    SELECT 
        c.Client_ID,
        c.CIN,
        c.Nom,
        c.Prenom,
        c.Date_Naissance,
        c.Email,
        c.Telephone,
        c.Adresse,
        c.Ville,
        tc.Libelle AS Type_Client,
        c.Date_Creation
    FROM CoreBanking_OLTP.dbo.Client c
    LEFT JOIN CoreBanking_OLTP.dbo.Type_Client tc 
        ON c.Type_Client_ID = tc.Type_Client_ID
    """
    
    try:
        results = oltp_conn.execute_query(query)
        logger.info(f"Extracted {len(results)} clients from OLTP")
        return results
    except Exception as e:
        logger.error(f"Error extracting clients: {e}")
        raise


def transform_clients(raw_data: list) -> list:
    """
    Transform client data to match DW structure
    
    Args:
        raw_data: Raw data from OLTP
        
    Returns:
        Transformed data ready for DW
    """
    transformed = []
    
    for row in raw_data:
        transformed.append({
            'Client_ID_Source': row[0],
            'CIN': row[1],
            'Nom': row[2],
            'Prenom': row[3],
            'Date_Naissance': row[4],
            'Email': row[5],
            'Telephone': row[6],
            'Adresse': row[7],
            'Ville': row[8],
            'Type_Client': row[9] if row[9] else 'Standard',
            'Date_Creation': row[10]
        })
    
    logger.info(f"Transformed {len(transformed)} client records")
    return transformed


def load_dim_client(dwh_conn: DWHConnection, transformed_data: list) -> dict:
    """
    Load transformed client data into DW Dim_Client table
    Performs UPDATE for existing clients and INSERT for new clients
    
    Args:
        dwh_conn: DWH database connection
        transformed_data: Transformed client data
        
    Returns:
        Dictionary with counts of inserted and updated rows
    """
    if not transformed_data:
        logger.warning("No data to load")
        return {'inserted': 0, 'updated': 0}
    
    # Get existing clients from DW using Client_ID_Source (stable business key)
    existing_clients_query = """
    SELECT Client_Key, Client_ID_Source, CIN, Nom, Prenom, Date_Naissance, Email, Telephone, Adresse, Ville, Type_Client, Date_Creation 
    FROM CoreBanking_DW.dbo.Dim_Client
    """
    existing_clients = {}
    
    try:
        existing_results = dwh_conn.execute_query(existing_clients_query)
        for row in existing_results:
            if row[1] is not None:
                existing_clients[row[1]] = {
                    'Client_Key': row[0],
                    'Client_ID_Source': row[1],
                    'CIN': row[2],
                    'Nom': row[3],
                    'Prenom': row[4],
                    'Date_Naissance': row[5],
                    'Email': row[6],
                    'Telephone': row[7],
                    'Adresse': row[8],
                    'Ville': row[9],
                    'Type_Client': row[10],
                    'Date_Creation': row[11]
                }
        logger.info(f"Found {len(existing_clients)} existing clients in DW")
    except Exception as e:
        logger.warning(f"Could not fetch existing clients: {e}")
    
    new_clients = []
    existing_clients_data = []
    
    for client in transformed_data:
        client_id_source = client['Client_ID_Source']
        if client_id_source in existing_clients:
            client['Client_Key'] = existing_clients[client_id_source]['Client_Key']
            existing_clients_data.append(client)
        else:
            new_clients.append(client)
    
    rows_inserted = 0
    rows_updated = 0
    
    try:
        cursor = dwh_conn.connection.cursor()
        
        # Insert new clients
        if new_clients:
            insert_query = """
            INSERT INTO CoreBanking_DW.dbo.Dim_Client 
            (Client_ID_Source, CIN, Nom, Prenom, Date_Naissance, Email, Telephone, Adresse, Ville, Type_Client, Date_Creation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            for client in new_clients:
                cursor.execute(insert_query, (
                    client['Client_ID_Source'],
                    client['CIN'],
                    client['Nom'],
                    client['Prenom'],
                    client['Date_Naissance'],
                    client['Email'],
                    client['Telephone'],
                    client['Adresse'],
                    client['Ville'],
                    client['Type_Client'],
                    client['Date_Creation']
                ))
                rows_inserted += 1
            
            logger.info(f"Inserted {rows_inserted} new clients")
        
        # Update existing clients - only if values have changed
        if existing_clients_data:
            for client in existing_clients_data:
                existing = existing_clients[client['Client_ID_Source']]
                
                # Check if any column has changed
                columns_to_update = []
                update_values = []
                
                if str(client['CIN']) != str(existing['CIN']):
                    columns_to_update.append('CIN = ?')
                    update_values.append(client['CIN'])
                
                if str(client['Nom']) != str(existing['Nom']):
                    columns_to_update.append('Nom = ?')
                    update_values.append(client['Nom'])
                
                if str(client['Prenom']) != str(existing['Prenom']):
                    columns_to_update.append('Prenom = ?')
                    update_values.append(client['Prenom'])
                
                if str(client['Date_Naissance']) != str(existing['Date_Naissance']):
                    columns_to_update.append('Date_Naissance = ?')
                    update_values.append(client['Date_Naissance'])
                
                if str(client['Email'] if client['Email'] else '') != str(existing['Email'] if existing['Email'] else ''):
                    columns_to_update.append('Email = ?')
                    update_values.append(client['Email'])
                
                if str(client['Telephone'] if client['Telephone'] else '') != str(existing['Telephone'] if existing['Telephone'] else ''):
                    columns_to_update.append('Telephone = ?')
                    update_values.append(client['Telephone'])
                
                if str(client['Adresse'] if client['Adresse'] else '') != str(existing['Adresse'] if existing['Adresse'] else ''):
                    columns_to_update.append('Adresse = ?')
                    update_values.append(client['Adresse'])
                
                if str(client['Ville'] if client['Ville'] else '') != str(existing['Ville'] if existing['Ville'] else ''):
                    columns_to_update.append('Ville = ?')
                    update_values.append(client['Ville'])
                
                if str(client['Type_Client']) != str(existing['Type_Client']):
                    columns_to_update.append('Type_Client = ?')
                    update_values.append(client['Type_Client'])
                
                if str(client['Date_Creation']) != str(existing['Date_Creation']):
                    columns_to_update.append('Date_Creation = ?')
                    update_values.append(client['Date_Creation'])
                
                # Only execute UPDATE if at least one column changed
                if columns_to_update:
                    update_query = f"""
                    UPDATE CoreBanking_DW.dbo.Dim_Client
                    SET {', '.join(columns_to_update)}
                    WHERE Client_Key = ?
                    """
                    update_values.append(client['Client_Key'])
                    cursor.execute(update_query, tuple(update_values))
                    rows_updated += 1
            
            logger.info(f"Updated {rows_updated} existing clients")
        
        dwh_conn.connection.commit()
        cursor.close()
        
        logger.info(f"Load completed: {rows_inserted} inserted, {rows_updated} updated")
        return {'inserted': rows_inserted, 'updated': rows_updated}
        
    except Exception as e:
        logger.error(f"Error loading clients: {e}")
        dwh_conn.connection.rollback()
        raise


def run_dim_client_etl(config: dict) -> dict:
    """
    Run complete ETL process for Dim_Client
    
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
        
        raw_data = extract_clients(oltp_conn)
        result['extracted'] = len(raw_data)
        
        # Transform
        logger.info("Starting transformation...")
        transformed_data = transform_clients(raw_data)
        result['transformed'] = len(transformed_data)
        
        # Load
        logger.info("Starting load to DW...")
        dwh_conn = DWHConnection(config)
        if not dwh_conn.connect():
            raise Exception("Failed to connect to DWH database")
        
        load_results = load_dim_client(dwh_conn, transformed_data)
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
    print("Starting Dim_Client ETL process...")
    results = run_dim_client_etl(config)
    
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
