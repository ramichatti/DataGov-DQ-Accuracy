import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataQuality.data_quality_engine import BaseQualityEngine, QualityIssue
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CreditQualityEngine(BaseQualityEngine):
    """Quality engine for Credit domain accuracy checks"""

    def __init__(self, oltp_conn, dwh_conn):
        super().__init__(oltp_conn, dwh_conn)

    def run_all_checks(self) -> dict:
        logger.info("Starting Credit domain accuracy checks...")

        results = {
            'montant_extreme_values': 0,
            'montant_decimal_precision': 0,
            'taux_interet_range_accuracy': 0,
            'date_debut_reasonable': 0,
            'montant_duree_consistency': 0,
            'credit_sans_client': 0,
            'duree_anormale': 0,
            'total_issues': 0
        }

        query = """
        SELECT Credit_ID, Montant
        FROM CoreBanking_OLTP.dbo.Credit
        WHERE Montant IS NOT NULL
        AND (ABS(Montant) > 10000000 OR (ABS(Montant) < 100 AND Montant <> 0))
        """
        results['montant_extreme_values'] = self.check_accuracy_validation(
            'Credit', 'Montant', query, 'Between 100 and 10M', 'High',
            'Credit amount has extreme values that may indicate data entry errors'
        )

        query = """
        SELECT Credit_ID, Montant
        FROM CoreBanking_OLTP.dbo.Credit
        WHERE Montant IS NOT NULL
        AND Montant <> ROUND(Montant, 3)
        """
        results['montant_decimal_precision'] = self.check_accuracy_validation(
            'Credit', 'Montant', query, 'Maximum 3 decimal places', 'Medium',
            'Credit amount should not exceed 3 decimal places for currency accuracy'
        )

        query = """
        SELECT Credit_ID, Taux_Interet
        FROM CoreBanking_OLTP.dbo.Credit
        WHERE Taux_Interet IS NOT NULL
        AND (Taux_Interet < 2 OR Taux_Interet > 25)
        """
        results['taux_interet_range_accuracy'] = self.check_accuracy_validation(
            'Credit', 'Taux_Interet', query, 'Between 2% and 25% (Tunisian market rates)', 'High',
            'Interest rate outside realistic range for Tunisian market may indicate data entry error'
        )

        query = """
        SELECT Credit_ID, Date_Debut
        FROM CoreBanking_OLTP.dbo.Credit
        WHERE Date_Debut IS NOT NULL
        AND (Date_Debut > GETDATE() OR Date_Debut < '2000-01-01')
        """
        results['date_debut_reasonable'] = self.check_accuracy_validation(
            'Credit', 'Date_Debut', query, 'Between 2000-01-01 and current date', 'High',
            'Credit start date must be reasonable (not in future, not before year 2000)'
        )

        query = """
        SELECT Credit_ID, Montant, Duree_Mois
        FROM CoreBanking_OLTP.dbo.Credit
        WHERE Montant IS NOT NULL AND Duree_Mois IS NOT NULL
        AND (Montant / Duree_Mois) < 10
        """
        results['montant_duree_consistency'] = self.check_accuracy_validation(
            'Credit', 'Montant', query, 'Monthly payment should be at least 10', 'High',
            'Credit amount and duration combination results in unrealistic monthly payment'
        )

        query = """
        SELECT Credit_ID, Client_ID
        FROM CoreBanking_OLTP.dbo.Credit
        WHERE Client_ID IS NULL
        """
        results['credit_sans_client'] = self.check_accuracy_validation(
            'Credit', 'Client_ID', query, 'Each credit must have an assigned client', 'High',
            'Credit has no associated client'
        )

        query = """
        SELECT Credit_ID, Duree_Mois
        FROM CoreBanking_OLTP.dbo.Credit
        WHERE Duree_Mois IS NOT NULL
        AND (Duree_Mois > 360 OR Duree_Mois < 1)
        """
        results['duree_anormale'] = self.check_accuracy_validation(
            'Credit', 'Duree_Mois', query, 'Duration must be between 1 and 360 months (30 years)', 'High',
            'Credit duration is outside realistic range'
        )

        self.enrich_issues_with_dimension_keys()

        results['total_issues'] = self.get_issues_count()
        logger.info(f"Credit quality checks completed. Total issues: {results['total_issues']}")

        return results

    def enrich_issues_with_dimension_keys(self):
        for issue in self.issues:
            try:
                query = f"""
                SELECT Client_ID, Date_Debut
                FROM CoreBanking_OLTP.dbo.Credit
                WHERE Credit_ID = {issue.ligne_id}
                """
                results = self.oltp_conn.execute_query(query)

                if results:
                    client_id = results[0][0]
                    date_debut = results[0][1]

                    issue.date_key = self.get_date_key(date_debut)

                    issue.credit_key = self.get_credit_key_by_id(issue.ligne_id)

                    if client_id:
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

        engine = CreditQualityEngine(oltp_conn, dwh_conn)
        results = engine.run_all_checks()

        print("\nCredit Quality Check Results:")
        for check, count in results.items():
            print(f"  {check}: {count}")

    finally:
        oltp_conn.disconnect()
        dwh_conn.disconnect()
