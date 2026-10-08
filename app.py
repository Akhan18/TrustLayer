from __future__ import annotations
import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from trustlayer.quality import validate_sales_data, REQUIRED_COLUMNS
from trustlayer.sample_data import make_sales_data
from trustlayer.storage import save_run, get_runs

ROOT = Path(__file__).resolve().parent
st.set_page_config(page_title="TrustLayer | Data Trust Console", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1500px;}
.hero {padding: 1.25rem 1.5rem; border: 1px solid rgba(120,130,150,.28); border-radius: 18px; background: linear-gradient(120deg, rgba(25,95,160,.13), rgba(20,170,140,.08));}
.hero h1 {margin: 0; letter-spacing: -1px;}
.hero p {margin: .45rem 0 0 0; opacity: .78;}
.small-muted {opacity: .7; font-size: .88rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>🛡️ TrustLayer</h1><p>From messy CSV to trusted dashboard · Explainable data quality and a controlled release gate</p></div>', unsafe_allow_html=True)
st.write("")

with st.sidebar:
    st.header("Data source")
    source_mode = st.radio("Choose input", ["Demo: intentionally messy sales data", "Demo: clean sales data", "Upload your CSV"], index=0)
    uploaded = None
    if source_mode == "Upload your CSV":
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
    st.divider()
    st.caption("TrustLayer MVP · Local-first · No API key required")
    st.caption("Rules are deterministic and every flagged row has an explanation.")

if source_mode == "Demo: intentionally messy sales data":
    source_df = make_sales_data(dirty=True)
    source_name = "demo_sales_messy.csv"
elif source_mode == "Demo: clean sales data":
    source_df = make_sales_data(dirty=False)
    source_name = "demo_sales_clean.csv"
else:
    if uploaded is None:
        st.info("Upload a CSV from the sidebar, or choose one of the built-in demo datasets to explore TrustLayer.")
        st.stop()
    try:
        source_df = pd.read_csv(uploaded)
        source_name = uploaded.name
    except Exception as exc:
        st.error(f"Could not read this CSV: {exc}")
        st.stop()

result = validate_sales_data(source_df)
summary = result.summary

# Persist each analysis run for the audit-history tab. Streamlit reruns are expected; avoid logging every widget rerun.
if "last_logged_signature" not in st.session_state:
    st.session_state.last_logged_signature = None
signature = f"{source_name}:{len(source_df)}:{summary['batch_status']}:{summary['issue_count']}:{summary['data_quality_score']}"
if st.session_state.last_logged_signature != signature:
    save_run(summary, source_name)
    st.session_state.last_logged_signature = signature

st.caption(f"Source: **{source_name}** · {len(source_df):,} rows · {len(source_df.columns)} columns")
if result.missing_columns:
    st.error("Schema check failed. Missing required columns: " + ", ".join(result.missing_columns))

# KPI row
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Rows received", f"{summary['total_rows']:,}")
c2.metric("Rows approved", f"{summary['approved_rows']:,}")
c3.metric("Rows quarantined", f"{summary['quarantined_rows']:,}")
c4.metric("Quality score", f"{summary['data_quality_score']:.1f}%")
c5.metric("Issues detected", f"{summary['issue_count']:,}")

status = summary["batch_status"]
if status == "APPROVED":
    st.success("RELEASE GATE: APPROVED — every row passed the configured critical checks.")
else:
    st.error("RELEASE GATE: BLOCKED — the batch contains critical issues. The approved output is not safe to publish as a complete batch.")

st.markdown("### Validation overview")
left, right = st.columns([1.05, 1])
with left:
    st.markdown("#### Issue types")
    if result.issues.empty:
        st.info("No issues detected. This batch passed all configured checks.")
    else:
        counts = result.issues.groupby(["rule_id", "severity"], dropna=False).size().reset_index(name="occurrences").sort_values("occurrences", ascending=False)
        fig = px.bar(counts, x="occurrences", y="rule_id", color="severity", orientation="h", text="occurrences", title="Rule violations detected")
        fig.update_layout(height=330, margin=dict(l=5, r=10, t=50, b=5), yaxis_title="", xaxis_title="Issue occurrences", legend_title="Severity")
        st.plotly_chart(fig, use_container_width=True)
with right:
    st.markdown("#### Release decision")
    if summary["total_rows"]:
        fig2 = px.pie(pd.DataFrame({"status": ["Approved", "Quarantined"], "rows": [summary["approved_rows"], summary["quarantined_rows"]]}), names="status", values="rows", hole=.62, title="Row disposition")
        fig2.update_layout(height=330, margin=dict(l=5, r=5, t=50, b=5), legend_title="")
        st.plotly_chart(fig2, use_container_width=True)
    st.caption("Quality score = approved rows ÷ total input rows × 100. A high score does not override a failed release gate.")

# Tabs
tab_preview, tab_issues, tab_exports, tab_history, tab_guide = st.tabs(["Data preview", "Issue log", "Exports", "Audit history", "How it works"])
with tab_preview:
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("#### Source preview")
        st.dataframe(source_df.head(20), use_container_width=True, hide_index=True)
    with p2:
        st.markdown("#### Approved records preview")
        st.dataframe(result.approved.head(20), use_container_width=True, hide_index=True)
    st.caption(f"Required sales schema: {', '.join(REQUIRED_COLUMNS)}")
with tab_issues:
    if result.issues.empty:
        st.success("No validation issues found.")
    else:
        filters = st.columns([1, 1, 2])
        rule_options = ["All"] + sorted(result.issues["rule_id"].dropna().unique().tolist())
        severity_options = ["All"] + sorted(result.issues["severity"].dropna().unique().tolist())
        selected_rule = filters[0].selectbox("Filter rule", rule_options)
        selected_severity = filters[1].selectbox("Filter severity", severity_options)
        search_text = filters[2].text_input("Search issue messages or values")
        filtered = result.issues.copy()
        if selected_rule != "All": filtered = filtered[filtered["rule_id"] == selected_rule]
        if selected_severity != "All": filtered = filtered[filtered["severity"] == selected_severity]
        if search_text:
            mask = filtered.astype(str).apply(lambda col: col.str.contains(search_text, case=False, na=False)).any(axis=1)
            filtered = filtered[mask]
        st.dataframe(filtered, use_container_width=True, hide_index=True)
        st.caption("Each issue points to a source row and includes a rule ID, field, value and remediation-oriented explanation.")
with tab_exports:
    st.markdown("#### Download artifacts")
    st.write("Use these exports to reproduce the result, review quarantined rows, or connect Power BI to the approved data.")
    a, b, c = st.columns(3)
    a.download_button("⬇ Approved rows CSV", result.approved.to_csv(index=False).encode("utf-8"), "trustlayer_approved.csv", "text/csv", use_container_width=True)
    b.download_button("⬇ Quarantined rows CSV", result.quarantined.to_csv(index=False).encode("utf-8"), "trustlayer_quarantine.csv", "text/csv", use_container_width=True)
    c.download_button("⬇ Issue log CSV", result.issues.to_csv(index=False).encode("utf-8"), "trustlayer_issues.csv", "text/csv", use_container_width=True)
    st.download_button("⬇ Validation summary JSON", json.dumps(summary, indent=2).encode("utf-8"), "trustlayer_validation_summary.json", "application/json")
    st.warning("Strict policy: if any critical row issues exist, batch status is BLOCKED. Approved rows are useful for review and diagnosis, but do not represent a complete approved batch until the source is fixed and revalidated.")
with tab_history:
    st.markdown("#### Recent validation runs")
    runs = get_runs()
    if runs:
        st.dataframe(pd.DataFrame(runs), use_container_width=True, hide_index=True)
    else:
        st.info("No runs have been recorded yet.")
    st.caption("Audit history is stored locally in outputs/trustlayer_audit.db on this machine.")
with tab_guide:
    st.markdown("""
    **Validation rules**
    - `REQUIRED_MISSING`: required identifier, dimension, date or numeric value is blank.
    - `DUPLICATE_ORDER_ID`: every occurrence of a duplicated order ID is flagged.
    - `INVALID_DATE`: nonblank dates that cannot be parsed are flagged.
    - `INVALID_NUMBER`: quantity or unit price cannot be parsed as a number.
    - `NON_POSITIVE_VALUE`: quantity and unit price must be greater than zero.
    - `SCHEMA_MISSING`: one or more required columns are absent; the batch is blocked.

    **Why no black-box AI?** These are explicit business rules. Deterministic checks are easier to test, explain to judges, and reproduce. AI can be added later for anomaly explanations, but it should not decide whether basic numeric or schema rules passed.

    **Power BI handoff**: download `trustlayer_approved.csv`, `trustlayer_quarantine.csv`, and `trustlayer_issues.csv`. See `POWER_BI_GUIDE.md` for suggested visuals and measures.
    """)

st.divider()
st.caption("TrustLayer is a hackathon MVP. Validate business-specific rules with the data owner before using it for production decisions.")
