"""Reproducible demo data; no network or Kaggle credentials required."""
from __future__ import annotations
import numpy as np
import pandas as pd

PRODUCTS = [
    ("Wireless Mouse", "Accessories", 699.0),
    ("USB-C Hub", "Accessories", 1899.0),
    ("Notebook", "Stationery", 99.0),
    ("Office Chair", "Furniture", 7499.0),
    ("Desk Lamp", "Home", 1299.0),
    ("Laptop Stand", "Accessories", 1499.0),
    ("Water Bottle", "Home", 499.0),
]
REGIONS = ["North", "South", "East", "West", "Central"]

def make_sales_data(rows: int = 250, dirty: bool = True, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    products = rng.integers(0, len(PRODUCTS), size=rows)
    data = {
        "order_id": [f"ORD-{100001+i}" for i in range(rows)],
        "order_date": pd.date_range("2026-01-01", periods=rows, freq="D").strftime("%Y-%m-%d").tolist(),
        "customer_id": [f"CUS-{int(x):04d}" for x in rng.integers(1, 181, size=rows)],
        "product": [PRODUCTS[i][0] for i in products],
        "category": [PRODUCTS[i][1] for i in products],
        "quantity": rng.integers(1, 6, size=rows).tolist(),
        "unit_price": [PRODUCTS[i][2] for i in products],
        "region": rng.choice(REGIONS, size=rows).tolist(),
    }
    df = pd.DataFrame(data)
    # Mixed invalid demo values are intentionally represented as strings/objects.
    df["quantity"] = df["quantity"].astype(object)
    df["unit_price"] = df["unit_price"].astype(object)
    if dirty and rows >= 30:
        # Deliberate, deterministic defects for a repeatable judging demo.
        df.loc[3, "customer_id"] = ""
        df.loc[8, "order_date"] = "not-a-date"
        df.loc[14, "quantity"] = -2
        df.loc[20, "unit_price"] = "not-a-price"
        df.loc[25, "product"] = None
        df.loc[30, "unit_price"] = 0
        df.loc[35, "order_id"] = df.loc[34, "order_id"]  # both copies are flagged
        df.loc[40, "quantity"] = "many"
        df.loc[45, "region"] = "   "
        df.loc[50, "order_date"] = ""
        df.loc[55, "unit_price"] = None
        df.loc[60, "customer_id"] = None
        df.loc[65, "quantity"] = 0
        df.loc[70, "category"] = ""
        df.loc[75, "order_id"] = df.loc[74, "order_id"]
        df.loc[80, "order_date"] = "31/31/2026"
        df.loc[85, "unit_price"] = -10
        df.loc[90, "product"] = "  "
        df.loc[95, "quantity"] = "2 units"
    return df
