# TrustLayer — From Messy CSV to Trusted Dashboard

A local-first hackathon MVP that validates sales CSV files before reporting. It produces explainable row-level issues, approved/quarantined exports, a strict release gate, a local SQLite audit history, and a Streamlit dashboard.

## Why this approach
- **Deterministic validation first:** easy to explain, test and reproduce; no model/API key required.
- **Local-first demo:** avoids cloud-account and workspace setup becoming a blocker.
- **Data contracts:** CSV/JSON outputs make it straightforward to connect Power BI or Microsoft Fabric later.
- **Auditability:** each finding contains a source row, rule ID, severity, column, value and explanation.

## Features
- CSV upload and built-in clean/messy demo datasets.
- Required schema checks, missing fields, duplicate order IDs, invalid dates, invalid numeric values, and non-positive quantity/price checks.
- Approved and quarantined row views, issue filters, quality score, charts, release status and downloads.
- Local audit run history stored in `outputs/trustlayer_audit.db`.
- Power BI handoff guide and unit tests.

## Setup — macOS (zsh) or Linux
Use Python 3.11 or 3.12 if available.

```bash
cd TrustLayer_MVP
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts_generate_sample_data.py
python -m pytest -q
python -m streamlit run app.py
```

Streamlit prints a local address, usually `http://localhost:8501`. Open it in your browser.

## Setup — Windows PowerShell

```powershell
cd TrustLayer_MVP
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts_generate_sample_data.py
python -m pytest -q
python -m streamlit run app.py
```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

## Demo script (about 3 minutes)
1. Choose **Demo: intentionally messy sales data**.
2. Point out the score, issue chart, and `BLOCKED` release gate.
3. Open **Issue log**, filter `DUPLICATE_ORDER_ID` or `INVALID_DATE`, and explain the row-level evidence.
4. Open **Exports** and download the issue log and quarantine CSV.
5. Switch to **Demo: clean sales data**. The gate should become `APPROVED` and the approved data will include calculated `revenue`.
6. Open **Audit history** to show both runs.
7. Explain how the approved CSV and issue exports connect to Power BI; use `POWER_BI_GUIDE.md`.

## Input schema
`order_id, order_date, customer_id, product, category, quantity, unit_price, region`

Dates should ideally be ISO `YYYY-MM-DD`. Quantity and unit price must be positive. Every `order_id` should be unique within the batch.

## Data policy
A row with any configured validation issue is quarantined. Missing required columns block the whole batch. The batch is approved only when all rows pass the critical checks. Do not treat the approved subset of a blocked batch as a fully released dataset.

## Kaggle dataset option
The demo is self-contained and doesn't need a Kaggle account. To test on a real-ish external dataset, download a CSV such as [Retail Store Sales — Dirty for Data Cleaning](https://www.kaggle.com/code/mahmoudredagamail/retail-store-sales-dirty-for-data-cleaning/input), then choose **Upload your CSV**. That dataset uses a different schema, so this MVP's sales-specific required-column rules will need a small schema mapping or a general-purpose profile mode before it can be used directly.

## Repository inspirations
- [data-quality-monitoring-dashboard](https://github.com/darshandharu/data-quality-monitoring-dashboard): pipeline + dashboard + Power BI handoff pattern.
- [AI Data Readiness Auditor](https://github.com/Sviless/ai-data-readiness-auditor): local-first upload, data quality/readiness reporting and export concepts.
- [Microsoft Fabric: Validate and clean up data](https://learn.microsoft.com/en-us/fabric/data-warehouse/validate-data): missing values, duplicates, calculations and valid ranges.

## Limitations and next steps
- Current rule set is tailored to sales CSVs; add configurable schemas for other domains.
- SQLite history is local to the machine and is not a multi-user database.
- No automatic repair: corrections should be reviewable and auditable rather than silently guessed.
- A future Fabric deployment can persist raw/approved/quarantine tables and schedule the pipeline.
