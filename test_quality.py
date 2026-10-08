import pandas as pd
from trustlayer.quality import validate_sales_data
from trustlayer.sample_data import make_sales_data


def test_clean_sample_passes():
    result = validate_sales_data(make_sales_data(rows=80, dirty=False))
    assert result.summary["batch_status"] == "APPROVED"
    assert result.summary["approved_rows"] == 80
    assert result.summary["quarantined_rows"] == 0
    assert result.issues.empty
    assert "revenue" in result.approved.columns


def test_dirty_sample_is_blocked_and_explained():
    result = validate_sales_data(make_sales_data(rows=100, dirty=True))
    assert result.summary["batch_status"] == "BLOCKED"
    assert result.summary["quarantined_rows"] > 0
    assert not result.issues.empty
    assert {"rule_id", "message", "source_row"}.issubset(result.issues.columns)


def test_missing_schema_blocks_whole_batch():
    df = pd.DataFrame({"order_id": ["A", "B"], "quantity": [1, 2]})
    result = validate_sales_data(df)
    assert result.summary["batch_status"] == "BLOCKED"
    assert result.summary["approved_rows"] == 0
    assert result.summary["quarantined_rows"] == 2
    assert "order_date" in result.missing_columns


def test_duplicate_ids_flag_every_occurrence():
    df = make_sales_data(rows=10, dirty=False)
    df.loc[1, "order_id"] = df.loc[0, "order_id"]
    result = validate_sales_data(df)
    duplicate_rows = result.issues[result.issues["rule_id"] == "DUPLICATE_ORDER_ID"]
    assert len(duplicate_rows) == 2
    assert result.summary["batch_status"] == "BLOCKED"


def test_input_is_not_mutated():
    df = make_sales_data(rows=10, dirty=False)
    before = df.copy(deep=True)
    validate_sales_data(df)
    pd.testing.assert_frame_equal(df, before)
