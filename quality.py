"""Rule-based validation for TrustLayer's sales-data MVP.

The validator is intentionally deterministic and explainable: every flagged row
has a rule ID, severity, and human-readable reason.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pandas as pd

REQUIRED_COLUMNS = [
    "order_id", "order_date", "customer_id", "product", "category",
    "quantity", "unit_price", "region",
]
NUMERIC_COLUMNS = ["quantity", "unit_price"]
CRITICAL_RULES = {"SCHEMA_MISSING", "REQUIRED_MISSING", "DUPLICATE_ORDER_ID", "INVALID_DATE", "INVALID_NUMBER", "NON_POSITIVE_VALUE"}

@dataclass
class ValidationResult:
    approved: pd.DataFrame
    quarantined: pd.DataFrame
    issues: pd.DataFrame
    summary: dict[str, Any]
    missing_columns: list[str]


def validate_sales_data(source: pd.DataFrame) -> ValidationResult:
    """Validate a sales dataframe and return approved/quarantined rows and issues.

    Input is copied and never modified in-place. Rows with any issue are quarantined.
    If required columns are missing, the entire batch is blocked because the schema
    cannot be evaluated reliably.
    """
    df = source.copy().reset_index(drop=True)
    df.insert(0, "source_row", range(1, len(df) + 1))
    missing_columns = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    issues: list[dict[str, Any]] = []
    row_issue_counts = {int(i): 0 for i in df.index}

    def add(mask: pd.Series, rule_id: str, severity: str, column: str, message: str) -> None:
        for idx in df.index[mask.fillna(False)]:
            issues.append({
                "source_row": int(df.at[idx, "source_row"]),
                "row_index": int(idx),
                "rule_id": rule_id,
                "severity": severity,
                "column": column,
                "value": _display_value(df.at[idx, column]) if column in df.columns else "<missing column>",
                "message": message,
            })
            row_issue_counts[int(idx)] += 1

    if missing_columns:
        issue_df = pd.DataFrame([{
            "source_row": None, "row_index": None, "rule_id": "SCHEMA_MISSING",
            "severity": "CRITICAL", "column": col, "value": "<missing column>",
            "message": f"Required column '{col}' is missing; this batch cannot be safely published.",
        } for col in missing_columns])
        summary = _summary(len(df), 0, len(df), issue_df, "BLOCKED", missing_columns)
        quarantined = df.copy()
        quarantined["quality_issues"] = "Missing required schema column(s)"
        return ValidationResult(pd.DataFrame(columns=list(df.columns) + ["revenue"]), quarantined, issue_df, summary, missing_columns)

    # Required business identifiers and dimensions must be present/nonblank.
    for col in ["order_id", "order_date", "customer_id", "product", "category", "region"]:
        raw = df[col]
        missing = raw.isna() | raw.astype("string").str.strip().eq("")
        add(missing, "REQUIRED_MISSING", "CRITICAL", col, f"Required field '{col}' is missing or blank.")

    # Duplicate order IDs: flag every occurrence so no ambiguous transaction is published.
    order_ids = df["order_id"].astype("string").str.strip()
    duplicate = order_ids.notna() & order_ids.ne("") & order_ids.duplicated(keep=False)
    add(duplicate, "DUPLICATE_ORDER_ID", "CRITICAL", "order_id", "Order ID occurs more than once in this batch.")

    parsed_dates = pd.to_datetime(df["order_date"], errors="coerce", format="mixed", dayfirst=False)
    date_nonblank = df["order_date"].notna() & df["order_date"].astype("string").str.strip().ne("")
    invalid_date = date_nonblank & parsed_dates.isna()
    add(invalid_date, "INVALID_DATE", "CRITICAL", "order_date", "Date cannot be parsed; use an unambiguous date such as YYYY-MM-DD.")

    numeric_values: dict[str, pd.Series] = {}
    for col in NUMERIC_COLUMNS:
        # Handle common formatting such as currency signs and thousands separators.
        cleaned = df[col].astype("string").str.replace(r"[$,£€]", "", regex=True).str.strip()
        parsed = pd.to_numeric(cleaned, errors="coerce")
        numeric_values[col] = parsed
        invalid = df[col].notna() & cleaned.ne("") & parsed.isna()
        add(invalid, "INVALID_NUMBER", "CRITICAL", col, f"'{col}' must contain a valid number.")
        missing_num = df[col].isna() | cleaned.eq("")
        add(missing_num, "REQUIRED_MISSING", "CRITICAL", col, f"Required numeric field '{col}' is missing.")
        non_positive = parsed.notna() & parsed.le(0)
        add(non_positive, "NON_POSITIVE_VALUE", "CRITICAL", col, f"'{col}' must be greater than zero.")

    issue_df = pd.DataFrame(issues, columns=["source_row", "row_index", "rule_id", "severity", "column", "value", "message"])
    bad_indices = {idx for idx, count in row_issue_counts.items() if count > 0}
    quarantined = df.loc[df.index.isin(bad_indices)].copy()
    approved = df.loc[~df.index.isin(bad_indices)].copy()

    # Add normalized business columns to approved records only. Raw source columns remain available.
    if not approved.empty:
        approved["order_date"] = pd.to_datetime(approved["order_date"], errors="coerce", format="mixed", dayfirst=False).dt.strftime("%Y-%m-%d")
        for col, values in numeric_values.items():
            approved[col] = values.loc[approved.index].astype(float)
        approved["revenue"] = approved["quantity"] * approved["unit_price"]
    else:
        approved["revenue"] = pd.Series(dtype=float)

    if not quarantined.empty:
        reasons = issue_df.groupby("row_index")["rule_id"].apply(lambda x: ", ".join(dict.fromkeys(x)))
        quarantined["quality_issues"] = quarantined.index.map(reasons).fillna("Review required")
    else:
        quarantined["quality_issues"] = pd.Series(dtype=str)

    status = "APPROVED" if len(df) > 0 and len(quarantined) == 0 else "BLOCKED"
    summary = _summary(len(df), len(approved), len(quarantined), issue_df, status, missing_columns)
    return ValidationResult(approved.reset_index(drop=True), quarantined.reset_index(drop=True), issue_df.drop(columns=["row_index"], errors="ignore"), summary, missing_columns)


def _display_value(value: Any) -> str:
    if pd.isna(value):
        return "<missing>"
    return str(value)[:160]


def _summary(total: int, approved: int, quarantined: int, issues: pd.DataFrame, status: str, missing_columns: list[str]) -> dict[str, Any]:
    score = round((approved / total) * 100, 2) if total else 0.0
    rule_counts = issues["rule_id"].value_counts().to_dict() if not issues.empty else {}
    return {
        "batch_status": status,
        "total_rows": int(total),
        "approved_rows": int(approved),
        "quarantined_rows": int(quarantined),
        "data_quality_score": score,
        "issue_count": int(len(issues)),
        "unique_rules_triggered": int(issues["rule_id"].nunique()) if not issues.empty else 0,
        "rule_counts": {str(k): int(v) for k, v in rule_counts.items()},
        "missing_columns": missing_columns,
        "policy": "Strict release gate: publish only when every row passes all critical checks.",
    }
