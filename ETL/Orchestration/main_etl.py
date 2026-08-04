"""
Main ETL Orchestration Script
Loads all dimension tables (except Dim_Date) in correct order, then loads Fact_Accuracy
"""

import sys
import os
import logging
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Dim.load_dim_agence import run_dim_agence_etl
from Dim.load_dim_client import run_dim_client_etl
from Dim.load_dim_compte import run_dim_compte_etl
from Dim.load_dim_transaction import run_dim_transaction_etl
from Dim.load_dim_credit import run_dim_credit_etl
from Dim.load_dim_date import run_dim_date_etl
from Fact.load_fact_accuracy import run_fact_accuracy_etl

# AI Data Governance Assistant (notification email + analyse Ollama)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
try:
    from AI.assistant import run_assistant
    from AI.email_notifier import is_email_configured
    AI_AVAILABLE = True
except Exception as _ai_import_err:  # pragma: no cover
    AI_AVAILABLE = False
    logger_ai_import_error = _ai_import_err

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Database configuration
config = {
    "dwh_server": "localhost",
    "dwh_database": "CoreBanking_DW",
    "oltp_server": "localhost",
    "oltp_database": "CoreBanking_OLTP",
    "trusted_connection": "yes",
    "username": "",
    "password": ""
}

def run_etl_pipeline():
    """Execute the complete ETL pipeline"""
    logger.info("=" * 80)
    logger.info("STARTING ETL PIPELINE")
    logger.info("=" * 80)
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    results = {}
    start_time = datetime.now()
    
    try:
        # =====================================================
        # STEP 1: LOAD DIMENSION TABLES (except Dim_Date)
        # =====================================================
        logger.info("STEP 1: LOADING DIMENSION TABLES")
        logger.info("-" * 80)
        
        # Load Dim_Date (generated, not from OLTP)
        logger.info("Loading Dim_Date...")
        try:
            result = run_dim_date_etl(config)
            results['Dim_Date'] = result
            logger.info(f"Dim_Date loaded successfully: {result}")
        except Exception as e:
            logger.error(f"Error loading Dim_Date: {e}")
            results['Dim_Date'] = {'status': 'error', 'error': str(e)}

        # Load Dim_Agence
        logger.info("Loading Dim_Agence...")
        try:
            result = run_dim_agence_etl(config)
            results['Dim_Agence'] = result
            logger.info(f"Dim_Agence loaded successfully: {result}")
        except Exception as e:
            logger.error(f"Error loading Dim_Agence: {e}")
            results['Dim_Agence'] = {'status': 'error', 'error': str(e)}
        
        # Load Dim_Client
        logger.info("Loading Dim_Client...")
        try:
            result = run_dim_client_etl(config)
            results['Dim_Client'] = result
            logger.info(f"Dim_Client loaded successfully: {result}")
        except Exception as e:
            logger.error(f"Error loading Dim_Client: {e}")
            results['Dim_Client'] = {'status': 'error', 'error': str(e)}
        
        # Load Dim_Compte
        logger.info("Loading Dim_Compte...")
        try:
            result = run_dim_compte_etl(config)
            results['Dim_Compte'] = result
            logger.info(f"Dim_Compte loaded successfully: {result}")
        except Exception as e:
            logger.error(f"Error loading Dim_Compte: {e}")
            results['Dim_Compte'] = {'status': 'error', 'error': str(e)}
        
        # Load Dim_Transaction
        logger.info("Loading Dim_Transaction...")
        try:
            result = run_dim_transaction_etl(config)
            results['Dim_Transaction'] = result
            logger.info(f"Dim_Transaction loaded successfully: {result}")
        except Exception as e:
            logger.error(f"Error loading Dim_Transaction: {e}")
            results['Dim_Transaction'] = {'status': 'error', 'error': str(e)}
        
        # Load Dim_Credit
        logger.info("Loading Dim_Credit...")
        try:
            result = run_dim_credit_etl(config)
            results['Dim_Credit'] = result
            logger.info(f"Dim_Credit loaded successfully: {result}")
        except Exception as e:
            logger.error(f"Error loading Dim_Credit: {e}")
            results['Dim_Credit'] = {'status': 'error', 'error': str(e)}
        
        logger.info("")
        logger.info("DIMENSION TABLES LOADING COMPLETED")
        logger.info("-" * 80)
        logger.info("")
        
        # =====================================================
        # STEP 2: LOAD FACT TABLE
        # =====================================================
        logger.info("STEP 2: LOADING FACT TABLE")
        logger.info("-" * 80)
        
        # Load Fact_Accuracy
        logger.info("Loading Fact_Accuracy...")
        try:
            result = run_fact_accuracy_etl(config)
            results['Fact_Accuracy'] = result
            logger.info(f"Fact_Accuracy loaded successfully: {result}")
        except Exception as e:
            logger.error(f"Error loading Fact_Accuracy: {e}")
            results['Fact_Accuracy'] = {'status': 'error', 'error': str(e)}
        
        logger.info("")
        logger.info("FACT TABLE LOADING COMPLETED")
        logger.info("-" * 80)
        logger.info("")
        
        # =====================================================
        # STEP 3: AI NOTIFICATION ASSISTANT
        # (analyse Ollama des issues actives + email automatique)
        # =====================================================
        ai_result = None
        if AI_AVAILABLE:
            try:
                fact_result = results.get('Fact_Accuracy', {})
                fact_status = fact_result.get('status', 'unknown')
                active_issues = fact_result.get('total_issues', 0)
                if fact_status == 'success' and active_issues and active_issues > 0:
                    logger.info("STEP 3: RUNNING AI NOTIFICATION ASSISTANT")
                    logger.info("-" * 80)
                    dwh_conn = None
                    try:
                        import pyodbc
                        conn_str = (
                            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                            f"SERVER={config['dwh_server']};"
                            f"DATABASE={config['dwh_database']};"
                            f"Trusted_Connection={config['trusted_connection']};"
                        )
                        dwh_conn = pyodbc.connect(conn_str, autocommit=True)
                        ai_model = os.environ.get("AI_MODEL", "llama3.2:3b")
                        execution_status = "SUCCESS"
                        ai_result = run_assistant(
                            dwh_conn,
                            model=ai_model,
                            execution_status=execution_status,
                        )
                        results['AI_Assistant'] = ai_result
                        if ai_result.get('email_sent'):
                            logger.info(f"AI Assistant: email envoyé ({ai_result['issues_count']} issues)")
                        else:
                            logger.info(f"AI Assistant: pas d'email ({ai_result.get('error', 'no issues')})")
                    except Exception as e:
                        logger.error(f"AI Assistant failed: {e}")
                        results['AI_Assistant'] = {'status': 'error', 'error': str(e)}
                    finally:
                        if dwh_conn is not None:
                            try:
                                dwh_conn.close()
                            except Exception:
                                pass
                else:
                    logger.info("AI Assistant: skipped (no active issues on this run).")
                    results['AI_Assistant'] = {'status': 'skipped', 'reason': 'no_issues'}
            except Exception as e:
                logger.error(f"AI Assistant pipeline error: {e}")
                results['AI_Assistant'] = {'status': 'error', 'error': str(e)}
        else:
            logger.info("AI Assistant: module non disponible (AI_AVAILABLE=False).")
            results['AI_Assistant'] = {'status': 'unavailable'}

        logger.info("")
        logger.info("AI NOTIFICATION STEP COMPLETED")
        logger.info("-" * 80)
        logger.info("")
        
        # =====================================================
        # SUMMARY
        # =====================================================
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("ETL PIPELINE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"End time: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total duration: {duration:.2f} seconds")
        logger.info("")
        
        logger.info("Results:")
        for table_name, result in results.items():
            status = result.get('status', 'unknown')
            if status == 'success':
                logger.info(f"  {table_name}: SUCCESS")
            else:
                logger.error(f"  {table_name}: FAILED - {result.get('error', 'Unknown error')}")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("ETL PIPELINE COMPLETED")
        logger.info("=" * 80)
        
        return results
        
    except Exception as e:
        logger.error(f"Fatal error in ETL pipeline: {e}")
        raise

if __name__ == "__main__":
    try:
        results = run_etl_pipeline()
        
        # Check if all steps succeeded
        all_success = all(
            result.get('status') == 'success' 
            for result in results.values()
        )
        
        if all_success:
            logger.info("All ETL steps completed successfully!")
            sys.exit(0)
        else:
            logger.warning("Some ETL steps failed. Check logs for details.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"ETL pipeline failed: {e}")
        sys.exit(1)
