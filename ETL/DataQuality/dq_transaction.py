import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataQuality.data_quality_engine import BaseQualityEngine, QualityIssue
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TransactionQualityEngine(BaseQualityEngine):
    """Quality engine for Transaction domain accuracy checks"""

    def __init__(self, oltp_conn, dwh_conn):
        super().__init__(oltp_conn, dwh_conn)

    def run_all_checks(self) -> dict:
        logger.info("Starting Transaction domain accuracy checks...")

        results = {
            'montant_extreme_values': 0,
            'montant_decimal_precision': 0,
            'date_transaction_reasonable': 0,
            'montant_type_consistency': 0,
            'transaction_sans_reference': 0,
            'transaction_compte_cloture': 0,
            'total_issues': 0
        }

        query = """
        SELECT Transaction_ID, Montant
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire
        WHERE Montant IS NOT NULL
        AND ABS(Montant) > 100000000
        """
        results['montant_extreme_values'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Montant', query, 'Between -100M and 100M', 'High',
            'Transaction amount has extreme values that may indicate data entry errors'
        )

        query = """
        SELECT Transaction_ID, Montant
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire
        WHERE Montant IS NOT NULL
        AND Montant <> ROUND(Montant, 3)
        """
        results['montant_decimal_precision'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Montant', query, 'Maximum 3 decimal places', 'Medium',
            'Transaction amount should not exceed 3 decimal places for currency accuracy'
        )

        query = """
        SELECT Transaction_ID, Date_Transaction
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire
        WHERE Date_Transaction IS NOT NULL
        AND (Date_Transaction > GETDATE() OR Date_Transaction < '2000-01-01')
        """
        results['date_transaction_reasonable'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Date_Transaction', query, 'Between 2000-01-01 and current date', 'High',
            'Transaction date must be reasonable (not in future, not before year 2000)'
        )

        query = """
        SELECT Transaction_ID, Montant, Type_Transaction
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire
        WHERE Type_Transaction = 'Virement' AND Montant <= 0
        """
        results['montant_type_consistency'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Montant', query, 'Virement transactions must have positive amount', 'High',
            'Transfer transactions with non-positive amounts indicate data inconsistency'
        )

        query = """
        SELECT Transaction_ID, Reference_Transaction
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire
        WHERE Reference_Transaction IS NULL OR Reference_Transaction = ''
        """
        results['transaction_sans_reference'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Reference_Transaction', query, 'Each transaction must have a reference', 'Medium',
            'Transaction is missing a reference number'
        )

        query = """
        SELECT t.Transaction_ID, t.Compte_ID
        FROM CoreBanking_OLTP.dbo.Transaction_Bancaire t
        JOIN CoreBanking_OLTP.dbo.Compte c ON t.Compte_ID = c.Compte_ID
        WHERE c.Statut = 'Cloture'
        """
        results['transaction_compte_cloture'] = self.check_accuracy_validation(
            'Transaction_Bancaire', 'Compte_ID', query, 'No transactions allowed on closed accounts', 'High',
            'Transaction posted on a closed account'
        )

        self.enrich_issues_with_dimension_keys()

        results['total_issues'] = self.get_issues_count()
        logger.info(f"Transaction quality checks completed. Total issues: {results['total_issues']}")

        return results

    def enrich_issues_with_dimension_keys(self):
        for issue in self.issues:
            try:
                query = f"""
                SELECT Compte_ID, Date_Transaction
                FROM CoreBanking_OLTP.dbo.Transaction_Bancaire
                WHERE Transaction_ID = {issue.ligne_id}
                """
                results = self.oltp_conn.execute_query(query)

                if results:
                    compte_id = results[0][0]
                    date_transaction = results[0][1]

                    issue.date_key = self.get_date_key(date_transaction)

                    issue.transaction_key = self.get_transaction_key_by_id(issue.ligne_id)

                    if compte_id:
                        issue.compte_key = self.get_compte_key_by_id(compte_id)

                        compte_query = f"""
                        SELECT Client_ID
                        FROM CoreBanking_OLTP.dbo.Compte
                        WHERE Compte_ID = {compte_id}
                        """
                        compte_results = self.oltp_conn.execute_query(compte_query)
                        if compte_results and compte_results[0][0]:
                            client_id = compte_results[0][0]
                            issue.client_key = self.get_client_key_by_id(client_id)

                            client_query = f"SELECT Agence_ID FROM CoreBanking_OLTP.dbo.Client WHERE Client_ID = {client_id}"
                            client_results = self.oltp_conn.execute_query(client_query)
                            if client_results and client_results[0][0]:
                                agence_id = client_results[0][0]
                                agence_query = f"SELECT Code_Agence FROM CoreBanking_OLTP.dbo.Agence WHERE Agence_ID = {agence_id}"
                                agence_results = self.oltp_conn.execute_query(agence_query)
                                if agence_results:
                                    issue.agence_key = self.get_agence_key_by_code(agence_results[0][0])

            except Exception as e:
                logger.warning(f"Could not enrich issue {issue.ligne_id}: {e}")


if __name__ == "__main__":
    from db_connection import OLTPConnection, DWHConnection

    config = {
        "dwh_server": "localhost",
        "dwh_database": "CoreBanking_DW",
        "oltp_server": "localhost",
        "oltp_database": "CoreBanking_OLTP",
        "trusted_connection": "yes",
        "username": "",
        "password": ""
    }

    oltp_conn = OLTPConnection(config)
    dwh_conn = DWHConnection(config)

    try:
        oltp_conn.connect()
        dwh_conn.connect()

        engine = TransactionQualityEngine(oltp_conn, dwh_conn)
        results = engine.run_all_checks()

        print("\nTransaction Quality Check Results:")
        for check, count in results.items():
            print(f"  {check}: {count}")

    finally:
        oltp_conn.disconnect()
        dwh_conn.disconnect()
