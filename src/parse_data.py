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

# 2. eBay Seller Hub transaction CSVs (2024-2025)

def parse_ebay_transactions():
    files = sorted(RAW.glob("Transaction_report_*.csv"))
    if not files:
        print(" [SKIP] No eBay transaction CSVs found")
        return pd.DataFrame()

    def clean_num(series):
        """Strip commas from currency strings before converting (handles $1,000+ values)"""
        return pd.to_numeric(
            series.astype(str).str.replace(",", "", regex=False),
            errors="coerce"
        ).fillna(0)

    frames = []
    for path in files:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.readlines()
        header_idx = next(
            (i for i, l in enumerate(lines)
             if l.startswith("Transaction creation date")),
             None
        )
        if header_idx is None:
            print(f"    [SKIP] No header in {path.name}")
            continue

        df = pd.read_csv(path, skiprows=header_idx, low_memory=False)
        df = df[df["Type"] == "Order"].copy()
        if df.empty:
            continue

        df["sold_date"] = pd.to_datetime(
            df["Transaction creation date"], format = "%b %d, %Y", errors="coerce"
        )
        df["revenue"]          = clean_num(df["Gross transaction amount"])
        df["item_subtotal"]    = clean_num(df["Item subtotal"])
        df["shipping_charged"] = clean_num(df["Shipping and handling"])
        fvf_fixed              = clean_num(df["Final Value Fee - fixed"]).abs()
        fvf_variable           = clean_num(df["Final Value Fee - variable"]).abs()
        df["platform_fee"]     = fvf_fixed + fvf_variable
        df["net_payout"]       = clean_num(df["Net amount"])
        df["name"]             = df["Item title"].fillna("Unknown").str[:80]
        df["platform"]         = "ebay"
        df["cog"]              = 0.0

        keep = ["name", "platform", "cog", "revenue", "item_subtotal",
                "shipping_charged", "platform_fee", "net_payout", "sold_date"]
        frames.append(df[keep])
        print(f"  ✓ {path.name}: {len(df)} orders")

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result = result[result["revenue"] > 0]
    result["sold_year"]  = result["sold_date"].dt.year
    result["sold_month"] = result["sold_date"].dt.month
    print(f"  → eBay total: {len(result)} orders")
    return result

# MAIN --------------------------------

if __name__ == "__main__":
    print("\n-- 2022 Flyp CSV exports--")
    items_df = parse_items_csv()
    if not items_df.empty:
        items_df.to_csv(OUT / "items_2022.csv", index=False)   

    print("\n── eBay Seller Hub CSVs ──")
    ebay_df = parse_ebay_transactions()
    if not ebay_df.empty:
        ebay_df.to_csv(OUT / "ebay_transactions.csv", index=False)

    print("\n Done.\n")    