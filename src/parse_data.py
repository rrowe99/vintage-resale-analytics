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

def parse_items_csvs():
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

# 3. Depop seller dashboard CSVs (2023-2025)

def parse_depop_sales():
    files = sorted(RAW.glob("Depop Sales*.csv"))
    if not files:
        print(" [SKIP] No Depop Sales CSVs found")
        return pd.DataFrame()

    def strip_dollar(series):
        return pd.to_numeric(
            series.astype(str).str.replace(r"[$,]", "", regex=True),
            errors="coerce"
        ).fillna(0)

    frames = []
    for path in files:
        df = pd.read_csv(path, low_memory=False).dropna(subset=["Date of sale"])
        df["sold_date"] = pd.to_datetime(df["Date of sale"], format="%m/%d/%Y", errors="coerce")
        df = df.dropna(subset=["sold_date"])
        df["name"]         = df["Description"].astype(str).str.split("\n").str[0].str.strip().str[:80]
        df["revenue"]      = strip_dollar(df["Item price"])
        df["shipping_rev"] = strip_dollar(df["Buyer shipping cost"])
        df["usps_cost"]    = strip_dollar(df["USPS Cost"])
        df["platform_fee"] = strip_dollar(df["Depop fee"]) + strip_dollar(df["Depop Payments fee"])
        df["net_payout"]   = df["revenue"] - df["platform_fee"] - df["usps_cost"]
        df["platform"]     = "depop"
        df["cog"]          = 0.0

        keep = ["name", "platform", "cog", "revenue", "shipping_rev",
                "usps_cost", "platform_fee", "net_payout", "sold_date"]
        frames.append(df[keep])
        print(f"  ✓ {path.name}: {len(df)} sales")

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result = result[result["revenue"] > 0]
    result["sold_year"]  = result["sold_date"].dt.year
    result["sold_month"] = result["sold_date"].dt.month
    print(f"  → Depop total: {len(result)} sales")
    return result

# MAIN --------------------------------

if __name__ == "__main__":
    print("\n-- 2022 Flyp CSV exports--")
    items_df = parse_items_csvs()
    if not items_df.empty:
        items_df.to_csv(OUT / "items_2022.csv", index=False)   

    print("\n── eBay Seller Hub CSVs ──")
    ebay_df = parse_ebay_transactions()
    if not ebay_df.empty:
        ebay_df.to_csv(OUT / "ebay_transactions.csv", index=False)

    print("\n── Depop Sales CSVs ──")
    depop_df = parse_depop_sales()
    if not depop_df.empty:
        depop_df.to_csv(OUT / "depop_sales.csv", index=False)

    print("\n Done.\n")    