from pathlib import Path
from trustlayer.sample_data import make_sales_data

ROOT = Path(__file__).resolve().parent
(ROOT / "data").mkdir(exist_ok=True)
make_sales_data(dirty=True).to_csv(ROOT / "data" / "sales_messy.csv", index=False)
make_sales_data(dirty=False).to_csv(ROOT / "data" / "sales_clean.csv", index=False)
print("Generated data/sales_messy.csv and data/sales_clean.csv")
