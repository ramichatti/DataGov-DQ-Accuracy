"""Entry point: run dims then fact ETL pipeline"""
from ETL.Orchestration.main_etl import run_etl_pipeline

if __name__ == "__main__":
    results = run_etl_pipeline()
    all_success = all(r.get('status') == 'success' for r in results.values())
    exit(0 if all_success else 1)
