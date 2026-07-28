# Data Governance & Accuracy

A banking data quality monitoring system that extracts transactional data from an OLTP source, maintains a star-schema data warehouse, and tracks data accuracy issues through a continuous ETL pipeline with a Power BI dashboard.

## Architecture

```
CoreBanking_OLTP ──► ETL Pipeline ──► CoreBanking_DW ──► Power BI
     (source)              │               (star-schema)      (dashboard)
                          ├── Dim tables (SCD Type 1)
                          ├── Fact_Accuracy (quality issues)
                          └── Auto-resolution tracking
```

### OLTP Source (`CoreBanking_OLTP`)

Normalized operational schema with tables: `Agence`, `Client`, `Type_Client`, `Compte`, `Type_Compte`, `Devise`, `Transaction_Bancaire`, `Credit`, `Statut_Client`.

### Data Warehouse (`CoreBanking_DW`)

Star-schema dimensional model:

| Table | Type | Grain |
|---|---|---|
| `Dim_Agence` | Dimension | Agency |
| `Dim_Client` | Dimension | Client |
| `Dim_Compte` | Dimension | Account |
| `Dim_Transaction` | Dimension | Transaction |
| `Dim_Credit` | Dimension | Credit |
| `Dim_Date` | Dimension | Date |
| `Fact_Accuracy` | Fact | Quality issue |

### ETL Pipeline

Runs as a two-phase batch process:

1. **Dimension Load** — Extracts, transforms, and loads (INSERT/UPDATE) each dimension table. Matching is done via stable `_ID_Source` business keys to prevent duplicate rows. Updates follow SCD Type 1 (in-place overwrite).

2. **Fact Load** — Runs domain-specific quality checks across Client, Compte, Transaction, and Credit domains. Results are stored in `Fact_Accuracy`. Previously unresolved issues are re-evaluated against current OLTP values; if the data has been corrected, the issue is marked `Solved = 1` with a `date_de_resolution` timestamp.

#### Quality Checks

| Domain | Columns Checked | Rules |
|---|---|---|
| Client | CIN, Telephone, Email, Date_Naissance | Format (8 digits), pattern (+216/00216), regex email, date range |
| Compte | Solde, Date_Ouverture, Statut | Numeric range, date range, business logic (closed → zero balance) |
| Transaction | Montant, Date_Transaction | Numeric range, precision, date range |
| Credit | Montant, Taux_Interet, Date_Debut | Numeric range, date range |

### Power BI Dashboard

`PowerBI/DQ_Accuracy_Report.pbix` provides a data quality scorecard with:

- Global accuracy score and SLA compliance (target >= 95%)
- Per-domain accuracy (Client, Compte, Transaction, Credit)
- Breakdown by agency, account type, transaction type, channel
- Trend view by month
- Measures defined in `PowerBI/DAX.txt`

## Project Structure

```
├── main.py                          # Entry point: runs dims then fact
├── DB/
│   ├── CoreBanking_OLTP.sql         # OLTP schema
│   ├── CoreBanking_DW.sql           # DWH schema
│   ├── Data.py / Data_Accuracy.py   # Sample data scripts
│   └── Delete_*.sql                 # Cleanup scripts
├── ETL/
│   ├── db_connection.py             # Database connection abstraction
│   ├── Dim/
│   │   ├── load_dim_agence.py
│   │   ├── load_dim_client.py
│   │   ├── load_dim_compte.py
│   │   ├── load_dim_transaction.py
│   │   ├── load_dim_credit.py
│   │   └── load_dim_date.py
│   ├── Fact/
│   │   └── load_fact_accuracy.py    # Quality checks + resolution logic
│   ├── DataQuality/
│   │   ├── data_quality_engine.py   # Core engine with key lookups
│   │   ├── dq_client.py
│   │   ├── dq_compte.py
│   │   ├── dq_transaction.py
│   │   └── dq_credit.py
│   └── Orchestration/
│       └── main_etl.py              # Pipeline coordinator
└── PowerBI/
    ├── DQ_Accuracy_Report.pbix      # Report file
    ├── DAX.txt                      # Measure definitions
    └── LogoDashboard.png
```

## Getting Started

### Prerequisites

- Python 3.x
- Microsoft SQL Server (local instance)
- Power BI Desktop

### Setup

```bash
# 1. Create databases and load schemas
sqlcmd -S localhost -i DB/CoreBanking_OLTP.sql
sqlcmd -S localhost -i DB/CoreBanking_DW.sql

# 2. Insert sample data
python DB/Data.py
python DB/Data_Accuracy.py

# 3. Run the ETL pipeline
python main.py
```

## Run

```bash
python main.py
```

The pipeline loads all dimensions then runs quality checks. Previous unresolved issues are automatically re-checked and marked `Solved = 1` with a resolution date when the OLTP data has been corrected.

## Automation (Windows Task Scheduler)

Schedule the ETL to run every 15 minutes:

```powershell
# Run as Administrator, then:
# Default: runs every 15 minutes
.\scripts\schedule_etl.ps1

# Custom interval and path
.\scripts\schedule_etl.ps1 -ProjectPath "C:\Your\Path" -IntervalMinutes 30
```

This creates a Windows scheduled task named `DataGov_DQ_ETL` that executes `main.py` at the specified interval. Logs are written to `logs\etl_YYYYMMDD.log`.
