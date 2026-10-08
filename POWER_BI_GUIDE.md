# TrustLayer → Power BI quick guide

## Fastest handoff
1. Run TrustLayer and open the **Exports** tab.
2. Download `trustlayer_approved.csv`, `trustlayer_issues.csv`, and `trustlayer_quarantine.csv`.
3. In Power BI Desktop, select **Get data → Text/CSV**, load the approved CSV, and select **Transform Data** to verify types.
4. Set `order_date` to Date, `quantity` to Whole Number, and `unit_price` / `revenue` to Decimal Number or Fixed Decimal Number.
5. Create a simple report with revenue by date, revenue by category, orders by region, and the audit summary from `trustlayer_validation_summary.json` (the JSON can also be loaded through Get Data → JSON).

## Suggested DAX measures

```DAX
Total Revenue = SUM(Approved[revenue])

Order Count = DISTINCTCOUNT(Approved[order_id])

Units Sold = SUM(Approved[quantity])

Average Order Value = DIVIDE([Total Revenue], [Order Count])
```

## Important release-gate behavior
TrustLayer uses a strict batch-level release gate. If any critical data issue exists, status is `BLOCKED`; the approved-row export is a diagnostic subset, not a declaration that the entire batch is ready to publish. Fix the source data and re-upload/re-run validation before treating the batch as approved.

## If Power BI Desktop is unavailable
Use the interactive Streamlit dashboard for the live demo and show the CSV/JSON exports as the integration contract. Power BI Desktop is not available natively on macOS; use a Windows machine or an available Power BI service environment if your team has one.
