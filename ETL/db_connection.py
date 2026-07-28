"""
Database Connection Module
Manages connections to CoreBanking DWH and OLTP databases
"""

import pyodbc
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)


class DWHConnection:
    """Manages connection to DWH database"""
    
    def __init__(self, config: Dict):
        """
        Initialize DWH connection with configuration
        
        Args:
            config: Dictionary containing database connection parameters
        """
        self.config = config
        self.connection = None
        self.server = config.get('dwh_server', 'localhost')
        self.database = config.get('dwh_database', 'CoreBanking_DWH')
        
    def get_connection_string(self) -> str:
        """
        Build SQL Server connection string for DWH
        
        Returns:
            Connection string for pyodbc
        """
        if self.config.get('trusted_connection', 'yes') == 'yes':
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"Trusted_Connection=yes;"
            )
        else:
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.config.get('username', '')};"
                f"PWD={self.config.get('password', '')};"
            )
    
    def connect(self) -> bool:
        """
        Establish connection to DWH database
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            connection_string = self.get_connection_string()
            self.connection = pyodbc.connect(connection_string)
            logger.info(f"Connected to DWH database: {self.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to DWH database: {e}")
            return False
    
    def disconnect(self):
        """Close DWH database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("DWH connection closed")
    
    def execute_query(self, query: str) -> List[Tuple]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query to execute
            
        Returns:
            List of tuples containing query results
        """
        if not self.connection:
            raise Exception("DWH connection not established")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_update(self, query: str) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query
        
        Args:
            query: SQL query to execute
            
        Returns:
            Number of rows affected
        """
        if not self.connection:
            raise Exception("DWH connection not established")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            rows_affected = cursor.rowcount
            cursor.close()
            return rows_affected
        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            self.connection.rollback()
            raise
    
    def test_connection(self) -> Dict[str, any]:
        """
        Test DWH database connection
        
        Returns:
            Dictionary with test results
        """
        result = {
            'database': 'DWH',
            'server': self.server,
            'database_name': self.database,
            'success': False,
            'error': None,
            'version': None
        }
        
        try:
            if self.connect():
                cursor = self.connection.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()
                result['version'] = version[0][:100] if version else None
                result['success'] = True
                cursor.close()
                self.disconnect()
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


class OLTPConnection:
    """Manages connection to OLTP database"""
    
    def __init__(self, config: Dict):
        """
        Initialize OLTP connection with configuration
        
        Args:
            config: Dictionary containing database connection parameters
        """
        self.config = config
        self.connection = None
        self.server = config.get('oltp_server', 'localhost')
        self.database = config.get('oltp_database', 'CoreBanking_OLTP')
        
    def get_connection_string(self) -> str:
        """
        Build SQL Server connection string for OLTP
        
        Returns:
            Connection string for pyodbc
        """
        if self.config.get('trusted_connection', 'yes') == 'yes':
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"Trusted_Connection=yes;"
            )
        else:
            return (
                f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                f"SERVER={self.server};"
                f"DATABASE={self.database};"
                f"UID={self.config.get('username', '')};"
                f"PWD={self.config.get('password', '')};"
            )
    
    def connect(self) -> bool:
        """
        Establish connection to OLTP database
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            connection_string = self.get_connection_string()
            self.connection = pyodbc.connect(connection_string)
            logger.info(f"Connected to OLTP database: {self.database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to OLTP database: {e}")
            return False
    
    def disconnect(self):
        """Close OLTP database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("OLTP connection closed")
    
    def execute_query(self, query: str) -> List[Tuple]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query to execute
            
        Returns:
            List of tuples containing query results
        """
        if not self.connection:
            raise Exception("OLTP connection not established")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_update(self, query: str) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query
        
        Args:
            query: SQL query to execute
            
        Returns:
            Number of rows affected
        """
        if not self.connection:
            raise Exception("OLTP connection not established")
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            self.connection.commit()
            rows_affected = cursor.rowcount
            cursor.close()
            return rows_affected
        except Exception as e:
            logger.error(f"Update execution failed: {e}")
            self.connection.rollback()
            raise
    
    def test_connection(self) -> Dict[str, any]:
        """
        Test OLTP database connection
        
        Returns:
            Dictionary with test results
        """
        result = {
            'database': 'OLTP',
            'server': self.server,
            'database_name': self.database,
            'success': False,
            'error': None,
            'version': None
        }
        
        try:
            if self.connect():
                cursor = self.connection.cursor()
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()
                result['version'] = version[0][:100] if version else None
                result['success'] = True
                cursor.close()
                self.disconnect()
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()


def test_connections(config: Dict) -> Dict[str, Dict]:
    """
    Test both DWH and OLTP database connections
    
    Args:
        config: Dictionary containing database connection parameters
        
    Returns:
        Dictionary with test results for both databases
    """
    results = {}
    
    # Test DWH connection
    dwh = DWHConnection(config)
    results['DWH'] = dwh.test_connection()
    
    # Test OLTP connection
    oltp = OLTPConnection(config)
    results['OLTP'] = oltp.test_connection()
    
    return results


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
    
    # Test connections
    print("Testing database connections...")
    results = test_connections(config)
    
    # Display results
    for db_name, result in results.items():
        print(f"\n{db_name} Database:")
        print(f"  Server: {result['server']}")
        print(f"  Database: {result['database_name']}")
        print(f"  Success: {result['success']}")
        if result['success']:
            print(f"  Version: {result['version']}")
        else:
            print(f"  Error: {result['error']}")
