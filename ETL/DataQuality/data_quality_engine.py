"""
Base Data Quality Engine for Accuracy Checks
Provides common functionality for detecting data quality accuracy issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import OLTPConnection, DWHConnection
import logging
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """Represents a data quality accuracy issue"""
    ligne_id: int
    table_name: str
    column_name: str
    valeur_erreur: str
    valeur_attendue: str
    error_message: str
    severity: str
    date_key: int
    client_key: int
    agence_key: int
    compte_key: int = None
    transaction_key: int = None
    credit_key: int = None
    solved: bool = False
    date_de_resolution = None


class BaseQualityEngine:
    """Base class for domain-specific quality engines"""
    
    def __init__(self, oltp_conn: OLTPConnection, dwh_conn: DWHConnection):
        self.oltp_conn = oltp_conn
        self.dwh_conn = dwh_conn
        self.issues: List[QualityIssue] = []
        self._default_client_key = self._get_default_client_key()
        self._default_agence_key = self._get_default_agence_key()
    
    def get_date_key(self, date_value) -> int:
        """Convert date to Date_ID format (YYYYMMDD)"""
        if date_value:
            try:
                if isinstance(date_value, str):
                    date_obj = datetime.strptime(date_value, '%Y-%m-%d')
                else:
                    date_obj = date_value
                date_key = int(date_obj.strftime('%Y%m%d'))
                # Check if this date exists in Dim_Date, if not use a default date
                try:
                    check_query = f"SELECT Date_ID FROM CoreBanking_DW.dbo.Dim_Date WHERE Date_ID = {date_key}"
                    results = self.dwh_conn.execute_query(check_query)
                    if results:
                        return date_key
                    else:
                        # Date doesn't exist in dimension, use 20200101 as default
                        return 20200101
                except:
                    return 20200101
            except:
                return 20200101
        return 20200101
    
    def _get_default_client_key(self) -> int:
        try:
            query = "SELECT MIN(Client_Key) FROM CoreBanking_DW.dbo.Dim_Client"
            results = self.dwh_conn.execute_query(query)
            if results and results[0][0]:
                return results[0][0]
        except:
            pass
        return 1

    def _get_default_agence_key(self) -> int:
        try:
            query = "SELECT MIN(Agence_Key) FROM CoreBanking_DW.dbo.Dim_Agence"
            results = self.dwh_conn.execute_query(query)
            if results and results[0][0]:
                return results[0][0]
        except:
            pass
        return 1

    def get_client_key_by_id(self, client_id: int) -> int:
        """Get Client_Key from DW by Client_ID_Source"""
        try:
            query = f"SELECT Client_Key FROM CoreBanking_DW.dbo.Dim_Client WHERE Client_ID_Source = {client_id}"
            results = self.dwh_conn.execute_query(query)
            if results:
                return results[0][0]
        except Exception as e:
            logger.warning(f"Could not find client key for ID {client_id}: {e}")
        return self._default_client_key

    def get_client_key_by_cin(self, cin: str) -> int:
        """Get Client_Key from DW by CIN"""
        try:
            query = f"SELECT Client_Key FROM CoreBanking_DW.dbo.Dim_Client WHERE CIN = '{cin}'"
            results = self.dwh_conn.execute_query(query)
            if results:
                return results[0][0]
        except Exception as e:
            logger.warning(f"Could not find client key for CIN {cin}: {e}")
        return self._default_client_key
    
    def get_agence_key_by_code(self, code_agence: str) -> int:
        """Get Agence_Key from DW by Code_Agence"""
        try:
            query = f"SELECT Agence_Key FROM CoreBanking_DW.dbo.Dim_Agence WHERE Code_Agence = '{code_agence}'"
            results = self.dwh_conn.execute_query(query)
            if results:
                return results[0][0]
        except Exception as e:
            logger.warning(f"Could not find agence key for code {code_agence}: {e}")
        return self._default_agence_key
    
    def get_compte_key_by_id(self, compte_id: int) -> int:
        """Get Compte_Key from DW by Compte_ID_Source"""
        try:
            query = f"SELECT Compte_Key FROM CoreBanking_DW.dbo.Dim_Compte WHERE Compte_ID_Source = {compte_id}"
            results = self.dwh_conn.execute_query(query)
            if results:
                return results[0][0]
        except Exception as e:
            logger.warning(f"Could not find compte key for ID {compte_id}: {e}")
        return None

    def get_compte_key_by_numero(self, numero_compte: str) -> int:
        """Get Compte_Key from DW by Numero_Compte"""
        try:
            query = f"SELECT Compte_Key FROM CoreBanking_DW.dbo.Dim_Compte WHERE Numero_Compte = '{numero_compte}'"
            results = self.dwh_conn.execute_query(query)
            if results:
                return results[0][0]
        except Exception as e:
            logger.warning(f"Could not find compte key for numero {numero_compte}: {e}")
        return None
    
    def get_transaction_key_by_id(self, transaction_id: int) -> int:
        """Get Transaction_Key from DW Dim_Transaction by Transaction_ID_Source"""
        try:
            query = f"SELECT Transaction_Key FROM CoreBanking_DW.dbo.Dim_Transaction WHERE Transaction_ID_Source = {transaction_id}"
            results = self.dwh_conn.execute_query(query)
            if results:
                return results[0][0]
            return None
        except Exception as e:
            logger.warning(f"Could not get Transaction_Key for ID {transaction_id}: {e}")
            return None
    
    def get_credit_key_by_id(self, credit_id: int) -> int:
        """Get Credit_Key from DW Dim_Credit by Credit_ID_Source"""
        try:
            query = f"SELECT Credit_Key FROM CoreBanking_DW.dbo.Dim_Credit WHERE Credit_ID_Source = {credit_id}"
            results = self.dwh_conn.execute_query(query)
            if results:
                return results[0][0]
            return None
        except Exception as e:
            logger.warning(f"Could not get Credit_Key for ID {credit_id}: {e}")
            return None
    
    def add_issue(self, issue: QualityIssue):
        """Add a quality issue to the list"""
        self.issues.append(issue)
    
    def clear_issues(self):
        """Clear all issues"""
        self.issues = []
    
    def get_issues_count(self) -> int:
        """Get total number of issues"""
        return len(self.issues)
    
    def check_null_values(self, table_name: str, column_name: str, 
                         query: str, severity: str = "Medium") -> int:
        """Check for null values in a column"""
        try:
            results = self.oltp_conn.execute_query(query)
            issues_found = 0
            
            for row in results:
                ligne_id = row[0]
                valeur_erreur = "NULL"
                valeur_attendue = "Non-NULL value"
                
                issue = QualityIssue(
                    ligne_id=ligne_id,
                    table_name=table_name,
                    column_name=column_name,
                    valeur_erreur=valeur_erreur,
                    valeur_attendue=valeur_attendue,
                    error_message=f"NULL value found in {column_name}",
                    severity=severity,
                    date_key=self.get_date_key(None),
                    client_key=self._default_client_key,
                    agence_key=self._default_agence_key
                )
                self.add_issue(issue)
                issues_found += 1
            
            if issues_found > 0:
                logger.info(f"Found {issues_found} NULL values in {table_name}.{column_name}")
            
            return issues_found
            
        except Exception as e:
            logger.error(f"Error checking NULL values: {e}")
            return 0
    
    def check_format_validation(self, table_name: str, column_name: str,
                                query: str, expected_format: str,
                                severity: str = "Medium") -> int:
        """Check for format validation issues"""
        try:
            results = self.oltp_conn.execute_query(query)
            issues_found = 0
            
            for row in results:
                ligne_id = row[0]
                valeur_erreur = str(row[1]) if row[1] else "NULL"
                valeur_attendue = expected_format
                
                issue = QualityIssue(
                    ligne_id=ligne_id,
                    table_name=table_name,
                    column_name=column_name,
                    valeur_erreur=valeur_erreur,
                    valeur_attendue=valeur_attendue,
                    error_message=f"Invalid format in {column_name}",
                    severity=severity,
                    date_key=self.get_date_key(None),
                    client_key=self._default_client_key,
                    agence_key=self._default_agence_key
                )
                self.add_issue(issue)
                issues_found += 1
            
            if issues_found > 0:
                logger.info(f"Found {issues_found} format issues in {table_name}.{column_name}")
            
            return issues_found
            
        except Exception as e:
            logger.error(f"Error checking format validation: {e}")
            return 0
    
    def check_range_validation(self, table_name: str, column_name: str,
                              query: str, min_value: Any = None, 
                              max_value: Any = None, severity: str = "Medium") -> int:
        """Check for range validation issues"""
        try:
            results = self.oltp_conn.execute_query(query)
            issues_found = 0
            
            for row in results:
                ligne_id = row[0]
                valeur_erreur = str(row[1]) if row[1] is not None else "NULL"
                valeur_attendue = f"Between {min_value} and {max_value}"
                
                issue = QualityIssue(
                    ligne_id=ligne_id,
                    table_name=table_name,
                    column_name=column_name,
                    valeur_erreur=valeur_erreur,
                    valeur_attendue=valeur_attendue,
                    error_message=f"Value out of range in {column_name}",
                    severity=severity,
                    date_key=self.get_date_key(None),
                    client_key=self._default_client_key,
                    agence_key=self._default_agence_key
                )
                self.add_issue(issue)
                issues_found += 1
            
            if issues_found > 0:
                logger.info(f"Found {issues_found} range issues in {table_name}.{column_name}")
            
            return issues_found
            
        except Exception as e:
            logger.error(f"Error checking range validation: {e}")
            return 0
    
    def check_referential_integrity(self, table_name: str, column_name: str,
                                   query: str, severity: str = "High") -> int:
        """Check for referential integrity issues"""
        try:
            results = self.oltp_conn.execute_query(query)
            issues_found = 0
            
            for row in results:
                ligne_id = row[0]
                valeur_erreur = str(row[1]) if row[1] else "NULL"
                valeur_attendue = "Valid foreign key reference"
                
                issue = QualityIssue(
                    ligne_id=ligne_id,
                    table_name=table_name,
                    column_name=column_name,
                    valeur_erreur=valeur_erreur,
                    valeur_attendue=valeur_attendue,
                    error_message=f"Orphaned record in {column_name}",
                    severity=severity,
                    date_key=self.get_date_key(None),
                    client_key=self._default_client_key,
                    agence_key=self._default_agence_key
                )
                self.add_issue(issue)
                issues_found += 1
            
            if issues_found > 0:
                logger.info(f"Found {issues_found} referential integrity issues in {table_name}.{column_name}")
            
            return issues_found
            
        except Exception as e:
            logger.error(f"Error checking referential integrity: {e}")
            return 0
    
    def check_accuracy_validation(self, table_name: str, column_name: str,
                                 query: str, expected_format: str,
                                 severity: str = "High", description: str = "") -> int:
        """Check for accuracy validation issues (data correctness)"""
        try:
            results = self.oltp_conn.execute_query(query)
            issues_found = 0
            
            for row in results:
                ligne_id = row[0]
                valeur_erreur = str(row[1]) if row[1] else "NULL"
                valeur_attendue = expected_format
                
                issue = QualityIssue(
                    ligne_id=ligne_id,
                    table_name=table_name,
                    column_name=column_name,
                    valeur_erreur=valeur_erreur,
                    valeur_attendue=valeur_attendue,
                    error_message=f"Inaccurate value in {column_name}: {description}",
                    severity=severity,
                    date_key=self.get_date_key(None),
                    client_key=self._default_client_key,
                    agence_key=self._default_agence_key
                )
                self.add_issue(issue)
                issues_found += 1
            
            if issues_found > 0:
                logger.info(f"Found {issues_found} accuracy issues in {table_name}.{column_name}")
            
            return issues_found
            
        except Exception as e:
            logger.error(f"Error checking accuracy validation: {e}")
            return 0
