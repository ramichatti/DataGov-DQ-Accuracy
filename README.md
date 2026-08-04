# Data Governance & Accuracy

A banking data quality monitoring system that extracts transactional data from an OLTP source, maintains a star-schema data warehouse, and tracks data accuracy issues through a continuous ETL pipeline with an **AI-powered email alerting module** (Ollama local) and a Power BI dashboard.

## Architecture

```
CoreBanking_OLTP ──► ETL Pipeline ──► CoreBanking_DW ──► Power BI
     (source)              │               (star-schema)      (dashboard)
                           ├── Dim tables (SCD Type 1)
                           ├── Fact_Accuracy (quality issues)
                           ├── Auto-resolution tracking
                           └── AI Assistant (Ollama) ──► Email alert
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

Runs as a three-phase batch process:

1. **Dimension Load** — Extracts, transforms, and loads (INSERT/UPDATE) each dimension table. Matching is done via stable `_ID_Source` business keys to prevent duplicate rows. Updates follow SCD Type 1 (in-place overwrite).

2. **Fact Load** — Runs domain-specific quality checks across Client, Compte, Transaction, and Credit domains. Results are stored in `Fact_Accuracy`. Previously unresolved issues are re-evaluated against current OLTP values; if the data has been corrected, the issue is marked `Solved = 1` with a `date_de_resolution` timestamp.

3. **AI Notification (optional)** — After the fact load, the `AI/assistant.py` module reads the active issues, asks a local Ollama model (`llama3.2:3b`) to produce a professional **business impact analysis** (explanation, root cause, business/financial impact, corrective action, risk level, priority), then sends a severity-prioritized HTML email via SMTP. Skipped automatically if Ollama is not running.

#### Quality Checks

| Domain | Columns Checked | Rules |
|---|---|---|
| Client | CIN, Telephone, Email, Date_Naissance | Format (8 digits), pattern (+216/00216), regex email, date range |
| Compte | Solde, Date_Ouverture, Statut | Numeric range, date range, business logic (closed → zero balance) |
| Transaction | Montant, Date_Transaction | Numeric range, precision, date range |
| Credit | Montant, Taux_Interet, Date_Debut | Numeric range, date range |

### Power BI Dashboard

`PowerBI/DG-DQ-Accuracy.pbix` provides a data quality scorecard with:

- Global accuracy score and SLA compliance (target >= 95%)
- Per-domain accuracy (Client, Compte, Transaction, Credit)
- Breakdown by agency, account type, transaction type, channel
- Trend view by month
- Measures defined in `PowerBI/DAX.txt`

### AI Data Governance Assistant (`AI/`)

Local, privacy-friendly notification module (no data leaves the machine):

| File | Role |
|---|---|
| `AI/ollama_client.py` | Thin client for the local Ollama server (`localhost:11434`) |
| `AI/assistant.py` | Orchestration: reads active issues from `Fact_Accuracy`, prompts the model, builds the HTML/text email |
| `AI/email_notifier.py` | Gmail SMTP sending (credentials from `.env`, app password) |

**AI analysis per issue** (7 fields, generated locally):

```
EXPLANATION:      what the error means in business language
ROOT_CAUSE:       most likely operational root cause
BUSINESS_IMPACT:  tangible impact on revenue / operations / compliance (BCT, Basel)
FINANCIAL_IMPACT: potential financial exposure estimate
CORRECTIVE_ACTION: concrete steps for the operations team
RISK_LEVEL:       Low | Medium | High
PRIORITY:         P1 | P2 | P3
```

The email sorts issues by severity (`High > Medium > Low`), shows KPI cards, a detailed error table, and one analysis card per issue with risk/priority badges.

## Project Structure

```
├── main.py                          # Entry point: runs dims, fact, then AI alert
├── AI/
│   ├── assistant.py                 # AI orchestration + email builder
│   ├── email_notifier.py            # SMTP Gmail sender (.env)
│   └── ollama_client.py             # Ollama local API client
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
│       └── main_etl.py              # Pipeline coordinator (STEP 3 = AI alert)
├── PowerBI/
│   ├── DG-DQ-Accuracy.pbix          # Report file
│   ├── DAX.txt                      # Measure definitions
│   └── Accuracy_Dashboard.pdf
├── scripts/
│   ├── run_etl.bat
│   ├── schedule_etl.ps1             # Windows Task Scheduler automation
│   └── generate_quality_rules_pdf.py
├── .env / .env.example              # SMTP + AI model configuration
└── docs/quality_rules.pdf
```

## Getting Started

### Prerequisites

- Python 3.x
- Microsoft SQL Server (local instance)
- Power BI Desktop
- [Ollama](https://ollama.com) (local LLM server, installed model `llama3.2:3b`) for AI analysis
- Gmail account with an **App Password** (for SMTP alerts)

### Setup

```bash
# 1. Create databases and load schemas
sqlcmd -S localhost -i DB/CoreBanking_OLTP.sql
sqlcmd -S localhost -i DB/CoreBanking_DW.sql

# 2. Insert sample data
python DB/Data.py
python DB/Data_Accuracy.py

# 3. Configure the AI notification module (copy from template)
copy .env.example .env
#    then edit SMTP_SENDER, SMTP_APP_PASSWORD, SMTP_RECEIVER, AI_MODEL

# 4. Start Ollama and pull the model
ollama serve
ollama pull llama3.2:3b

# 5. Run the ETL pipeline
python main.py
```

### Installed Python dependencies

```
pyodbc
requests
python-dotenv
```

## Run

```bash
python main.py
```

The pipeline loads all dimensions, runs quality checks, and then:
- previous unresolved issues are automatically re-checked and marked `Solved = 1` with a resolution date when the OLTP data has been corrected;
- the AI assistant analyzes the remaining active issues with the local Ollama model and sends a severity-prioritized email alert to `SMTP_RECEIVER`.

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

## Email Configuration (`.env`)

| Variable | Example | Purpose |
|---|---|---|
| `SMTP_SERVER` | `smtp.gmail.com` | SMTP host |
| `SMTP_PORT` | `587` | SMTP port (STARTTLS) |
| `SMTP_SENDER` | `you@gmail.com` | Sender address |
| `SMTP_APP_PASSWORD` | `xxxx xxxx xxxx xxxx` | Gmail App Password (16 chars) |
| `SMTP_RECEIVER` | `team@example.com` | Alert recipient(s) |
| `AI_MODEL` | `llama3.2:3b` | Ollama model used for analysis |

Create it by copying `.env.example`. The `.env` file is gitignored — never commit real credentials. The project falls back to environment variables if `.env` is missing; sending is skipped when no SMTP credentials are configured.
