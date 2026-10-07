"""
parse_data.py - Vintage Resale Analytics
----------------------------------------
Extracts and cleans sales data from raw source files into structured CSVs that feed the analysis notebook.

Run from the project root: 
    python src/parse_data.py

Reads from: data/raw/
Writes to:  data/processed/
"""

import pandas as pd
from pathlib import Path

BASE = Path(__file__).parent.parent
RAW = BASE / "data" / "raw"
OUT = BASE / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# 1. 2022 Flyp CSV exports (item level: Grailed + eBay)

def parse_items_csv():
    csv_files = {
        "Paypal 2022 COG.csv": "grailed",
        "eBay 2022 COG.csv": "ebay",
    }
    frames = []
    for filename, default_platform in csv_files.items():
        path = RAW / filename
        if not path.exists():
            print(f"    [SKIP] {filename}")
            continue
        df = pd.read_csv(path, low_memory=False)
        df = df[df["sold"] == True].copy()
        df["platform"]      = df["platform_name"].fillna(default_platform).str.lower()
        df["sold_date"]     = pd.to_datetime(df["sold_at"],      utc=True, errors="coerce")
        df["purchase_date"] = pd.to_datetime(df["purchased_at"], utc=True, errors="coerce")
        df["cog"]           = pd.to_numeric(df["purchase_price"], errors="coerce").fillna(0)
        df["revenue"]       = pd.to_numeric(df["payout_amount"],  errors="coerce").fillna(0)
        df["profit"]        = df["revenue"] - df["cog"]
        df["roi_pct"]       = pd.to_numeric((df["profit"] / df["cog"].replace(0, float("nan"))) * 100, errors="coerce")
        keep = ["name", "brand", "condition", "cog", "revenue", "profit", "roi_pct",
                "platform", "sold_date", "purchase_date"]
        frames.append(df[keep])

    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    result = result[result["revenue"] > 0]
    result["sold_year"] = result["sold_date"].dt.year
    result["sold_month"] = result["sold_date"].dt.month
    print(f"  ✓ Flyp CSVs: {len(result)} sold items")
    return result


# MAIN --------------------------------

if __name__ == "__main__":
    print("\n-- 2022 Flyp CSV exports--")
    items_df = parse_items_csv()
    if not items_df.empty:
        items_df.to_csv(OUT / "items_2022.csv", index=False)

    print("\n Done.\n")    