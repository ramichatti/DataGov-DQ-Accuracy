# Data Governance & Accuracy Project

ETL pipeline for banking data quality monitoring.

## Structure

- `ETL/Dim/` — Dimension table loaders (Agence, Client, Compte, Transaction, Credit)
- `ETL/Fact/` — Fact_Accuracy loader with quality issue resolution tracking
- `ETL/DataQuality/` — Domain-specific quality checks and enrichment
- `ETL/Orchestration/` — Pipeline orchestration
- `DB/` — Database schemas

## Run

```bash
python main.py
```

Loads all dimensions then runs quality checks and populates Fact_Accuracy. Unresolved issues are re-checked and marked `Solved=1` with a resolution date when the OLTP data is corrected.
