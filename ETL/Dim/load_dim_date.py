"""
ETL Process for Dim_Date
Generates date dimension data from 2020 to June 2026 and loads into DW.Dim_Date
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import DWHConnection
import logging
from datetime import datetime, date
import calendar

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_dates(start_year: int = 2020, end_year: int = 2026, end_month: int = 6) -> list:
    """
    Generate date dimension data from start_year to end_year/end_month
    
    Args:
        start_year: Start year (default 2020)
        end_year: End year (default 2026)
        end_month: End month (default 6 for June)
        
    Returns:
        List of dictionaries containing date dimension data
    """
    dates = []
    
    start_date = date(start_year, 1, 1)
    end_date = date(end_year, end_month, 30)  # June 30, 2026
    
    current_date = start_date
    
    while current_date <= end_date:
        # Calculate Date_ID as YYYYMMDD
        date_id = int(current_date.strftime('%Y%m%d'))
        
        # Day information
        day_number = current_date.day
        day_name = current_date.strftime('%A')
        
        # Week information
        week_number = current_date.isocalendar()[1]
        
        # Month information
        month_number = current_date.month
        month_name = current_date.strftime('%B')
        
        # Quarter information
        quarter_number = (current_date.month - 1) // 3 + 1
        
        # Year information
        year_number = current_date.year
        
        # Weekend check (Saturday=5, Sunday=6)
        is_weekend = 1 if current_date.weekday() >= 5 else 0
        
        dates.append({
            'Date_ID': date_id,
            'Full_Date': current_date,
            'Day_Number': day_number,
            'Day_Name': day_name,
            'Week_Number': week_number,
            'Month_Number': month_number,
            'Month_Name': month_name,
            'Quarter_Number': quarter_number,
            'Year_Number': year_number,
            'Is_Weekend': is_weekend
        })
        
        current_date = date.fromordinal(current_date.toordinal() + 1)
    
    logger.info(f"Generated {len(dates)} dates from {start_date} to {end_date}")
    return dates


def load_dim_date(dwh_conn: DWHConnection, date_data: list) -> dict:
    """
    Load date dimension data into DW Dim_Date table
    Performs UPDATE for existing dates and INSERT for new dates
    
    Args:
        dwh_conn: DWH database connection
        date_data: Date dimension data
        
    Returns:
        Dictionary with counts of inserted and updated rows
    """
    if not date_data:
        logger.warning("No data to load")
        return {'inserted': 0, 'updated': 0}
    
    # Get existing dates from DW
    existing_dates_query = """
    SELECT Date_ID, Full_Date FROM CoreBanking_DW.dbo.Dim_Date
    """
    existing_dates = {}
    
    try:
        existing_results = dwh_conn.execute_query(existing_dates_query)
        existing_dates = {row[0]: row[1] for row in existing_results}
        logger.info(f"Found {len(existing_dates)} existing dates in DW")
    except Exception as e:
        logger.warning(f"Could not fetch existing dates: {e}")
    
    # Separate new and existing dates
    new_dates = []
    existing_dates_data = []
    
    for date_record in date_data:
        if date_record['Date_ID'] in existing_dates:
            existing_dates_data.append(date_record)
        else:
            new_dates.append(date_record)
    
    rows_inserted = 0
    rows_updated = 0
    
    try:
        cursor = dwh_conn.connection.cursor()
        
        # Insert new dates
        if new_dates:
            insert_query = """
            INSERT INTO CoreBanking_DW.dbo.Dim_Date 
            (Date_ID, Full_Date, Day_Number, Day_Name, Week_Number, Month_Number, 
             Month_Name, Quarter_Number, Year_Number, Is_Weekend)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            for date_record in new_dates:
                cursor.execute(insert_query, (
                    date_record['Date_ID'],
                    date_record['Full_Date'],
                    date_record['Day_Number'],
                    date_record['Day_Name'],
                    date_record['Week_Number'],
                    date_record['Month_Number'],
                    date_record['Month_Name'],
                    date_record['Quarter_Number'],
                    date_record['Year_Number'],
                    date_record['Is_Weekend']
                ))
                rows_inserted += 1
            
            logger.info(f"Inserted {rows_inserted} new dates")
        
        # Update existing dates (if needed - typically dates don't change)
        if existing_dates_data:
            update_query = """
            UPDATE CoreBanking_DW.dbo.Dim_Date
            SET Full_Date = ?, Day_Number = ?, Day_Name = ?, Week_Number = ?, 
                Month_Number = ?, Month_Name = ?, Quarter_Number = ?, 
                Year_Number = ?, Is_Weekend = ?
            WHERE Date_ID = ?
            """
            
            for date_record in existing_dates_data:
                cursor.execute(update_query, (
                    date_record['Full_Date'],
                    date_record['Day_Number'],
                    date_record['Day_Name'],
                    date_record['Week_Number'],
                    date_record['Month_Number'],
                    date_record['Month_Name'],
                    date_record['Quarter_Number'],
                    date_record['Year_Number'],
                    date_record['Is_Weekend'],
                    date_record['Date_ID']
                ))
                rows_updated += 1
            
            logger.info(f"Updated {rows_updated} existing dates")
        
        dwh_conn.connection.commit()
        cursor.close()
        
        logger.info(f"Load completed: {rows_inserted} inserted, {rows_updated} updated")
        return {'inserted': rows_inserted, 'updated': rows_updated}
        
    except Exception as e:
        logger.error(f"Error loading dates: {e}")
        dwh_conn.connection.rollback()
        raise


def run_dim_date_etl(config: dict, start_year: int = 2020, end_year: int = 2026, end_month: int = 6) -> dict:
    """
    Run complete ETL process for Dim_Date
    
    Args:
        config: Database configuration dictionary
        start_year: Start year (default 2020)
        end_year: End year (default 2026)
        end_month: End month (default 6 for June)
        
    Returns:
        Dictionary with ETL results
    """
    result = {
        'status': 'failed',
        'generated': 0,
        'inserted': 0,
        'updated': 0,
        'error': None,
        'timestamp': datetime.now().isoformat()
    }
    
    dwh_conn = None
    
    try:
        # Generate
        logger.info(f"Starting date generation from {start_year} to {end_year}-{end_month}...")
        date_data = generate_dates(start_year, end_year, end_month)
        result['generated'] = len(date_data)
        
        # Load
        logger.info("Starting load to DW...")
        dwh_conn = DWHConnection(config)
        if not dwh_conn.connect():
            raise Exception("Failed to connect to DWH database")
        
        load_results = load_dim_date(dwh_conn, date_data)
        result['inserted'] = load_results['inserted']
        result['updated'] = load_results['updated']
        
        result['status'] = 'success'
        logger.info("ETL process completed successfully")
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"ETL process failed: {e}")
        
    finally:
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
    print("Starting Dim_Date ETL process...")
    results = run_dim_date_etl(config, start_year=2020, end_year=2026, end_month=6)
    
    # Display results
    print("\nETL Results:")
    print(f"  Status: {results['status']}")
    print(f"  Generated: {results['generated']}")
    print(f"  Inserted: {results['inserted']}")
    print(f"  Updated: {results['updated']}")
    print(f"  Timestamp: {results['timestamp']}")
    
    if results['error']:
        print(f"  Error: {results['error']}")
