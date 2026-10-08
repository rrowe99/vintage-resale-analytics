"""
parse_data.py - Vintage Resale Analytics
----------------------------------------
Extracts and cleans sales data from raw source files into structured CSVs that feed the analysis notebook.

Run from the project root: 
    python src/parse_data.py

Reads from: data/raw/
Writes to:  data/processed/
"""

import re
import pandas as pd
import pdfplumber
from pathlib import Path

BASE = Path(__file__).parent.parent
RAW = BASE / "data" / "raw"
OUT = BASE / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# 1. 2022 Flyp CSV exports (item level: Grailed + eBay)

def parse_item_csvs():
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
        print("  [SKIP] No eBay transaction CSVs found")
        return pd.DataFrame()

    def clean_num(series):
        """Strip commas from currency strings before converting (handles $1,000+ values)."""
        return pd.to_numeric(
            series.astype(str).str.replace(",", "", regex=False),
            errors="coerce"
        ).fillna(0)

    # Read every file first: a refund can land in a later file than its order
    frames = []
    for path in files:
        with open(path, encoding="utf-8-sig") as f:
            lines = f.readlines()
        header_idx = next(
            (i for i, l in enumerate(lines) if l.startswith("Transaction creation date")),
            None
        )
        if header_idx is None:
            print(f"  [SKIP] No header in {path.name}")
            continue
        raw_file = pd.read_csv(path, skiprows=header_idx, low_memory=False)
        frames.append(raw_file)
        print(f"  ✓ {path.name}: {(raw_file['Type'] == 'Order').sum()} orders")

    if not frames:
        return pd.DataFrame()
    raw = pd.concat(frames, ignore_index=True)

    # Refunds are separate rows, linked to the original sale by order number
    refunds = raw[raw["Type"] == "Refund"].copy()
    refunds["refund_amount"] = clean_num(refunds["Gross transaction amount"]).abs()
    refund_totals = refunds.groupby("Order number")["refund_amount"].sum()

    df = raw[raw["Type"] == "Order"].copy()
    df["revenue"] = clean_num(df["Gross transaction amount"])
    refunded = df["Order number"].map(refund_totals).fillna(0)
    fully_refunded = refunded >= df["revenue"]
    df = df[~fully_refunded].copy()
    print(f"  → removed {fully_refunded.sum()} fully refunded orders")

    df["sold_date"]        = pd.to_datetime(df["Transaction creation date"], format="%b %d, %Y", errors="coerce")
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
    result = df[df["revenue"] > 0][keep].copy()
    result["sold_year"]  = result["sold_date"].dt.year
    result["sold_month"] = result["sold_date"].dt.month
    print(f"  → eBay total: {len(result)} orders")
    return result

# 3. Depop seller dashboard CSVs (2023-2025)

def parse_depop_sales():
    files = sorted(RAW.glob("Depop Sales*.csv"))
    if not files:
        print("  [SKIP] No Depop Sales CSVs found")
        return pd.DataFrame()

    def strip_dollar(series):
        return pd.to_numeric(
            series.astype(str).str.replace(r"[$,]", "", regex=True),
            errors="coerce"
        ).fillna(0)

    frames = []
    for path in files:
        raw_file = pd.read_csv(path, low_memory=False).dropna(subset=["Date of sale"])
        frames.append(raw_file)
        print(f"  ✓ {path.name}: {len(raw_file)} sales")
    raw = pd.concat(frames, ignore_index=True)

    # Export date ranges overlap (Dec 2023 is in two files), so drop rows that appear twice
    before = len(raw)
    raw = raw.drop_duplicates(subset=["Date of sale", "Time of sale", "Description", "Item price"])
    print(f"  → removed {before - len(raw)} duplicate rows from overlapping exports")

    # Sales refunded in full never became revenue
    fully_refunded = strip_dollar(raw["Refunded to buyer amount"]) >= strip_dollar(raw["Item price"])
    df = raw[~fully_refunded].copy()
    print(f"  → removed {fully_refunded.sum()} fully refunded sales")

    df["sold_date"]    = pd.to_datetime(df["Date of sale"], format="%m/%d/%Y", errors="coerce")
    df = df.dropna(subset=["sold_date"]).copy()
    df["listed_date"]  = pd.to_datetime(df["Date of listing"], format="%m/%d/%Y", errors="coerce")
    df["name"]         = df["Description"].astype(str).str.split("\n").str[0].str.strip().str[:80]
    df["revenue"]      = strip_dollar(df["Item price"])
    df["shipping_rev"] = strip_dollar(df["Buyer shipping cost"])
    df["usps_cost"]    = strip_dollar(df["USPS Cost"])
    df["platform_fee"] = strip_dollar(df["Depop fee"]) + strip_dollar(df["Depop Payments fee"])
    df["net_payout"]   = df["revenue"] - df["platform_fee"] - df["usps_cost"]
    df["brand"]        = df["Brand"]
    df["category"]     = df["Category"]
    df["platform"]     = "depop"
    df["cog"]          = 0.0

    result = df[df["revenue"] > 0].copy()
    result["sold_year"]  = result["sold_date"].dt.year
    result["sold_month"] = result["sold_date"].dt.month
    result = result[["name", "platform", "cog", "revenue", "shipping_rev", "usps_cost",
                     "platform_fee", "net_payout", "sold_date", "sold_year", "sold_month",
                     "listed_date", "brand", "category"]]
    print(f"  → Depop total: {len(result)} sales")
    return result

# 4. 1099-K PDFs (monthly revenue by platform)

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
    "august":8, "september": 9, "october": 10, "november": 11, "december": 12,
}

def _extract_1099_monthly(pdf_path, platform, year):
    records = []
    with pdfplumber.open(pdf_path) as pdf:
        tables = pdf.pages[0].extract_tables()
        for table in tables:
            for row in (table or []):
                for cell in (row or []):
                    if not cell:
                        continue
                    matches = re.findall(
                    r'5[a-l]\s+(\w+)\s*\$\s*([\d,]+\.?\d*)',
                        cell, re.IGNORECASE
                    )
                    for month_name, amount_str in matches:
                        month_num = MONTH_MAP.get(month_name.lower())
                        if month_num:
                            amount = float(amount_str.replace(",", ""))
                            if amount > 0:
                                records.append({
                                    "year": year, "month": month_num,
                                    "platform": platform, "gross_revenue": amount,
                                })
    return records

def parse_1099s():
    files = [("Paypal_1099K_2022.pdf",         "grailed", 2022),
        ("eBay_1099-K_2022.pdf",          "ebay",    2022),
        ("eBay_1099-K_2023.pdf",          "ebay",    2023),
        ("DEPOPtax_form_1099k_2023.pdf",  "depop",   2023),
        ("ebay_1099-K_2024.pdf",          "ebay",    2024),
        ("depop_tax_form_1099k_2024.pdf", "depop",   2024),
        ("eBay_1099-K_2025.pdf",          "ebay",    2025),
        ("Depop_tax_form_1099k_2025.pdf", "depop",   2025),
    ]
    all_records = []
    for filename, platform, year in files:
        path = RAW / filename
        if not path.exists():
            print(f"    [SKIP] {filename}")
            continue
        records = _extract_1099_monthly(path, platform, year)
        all_records.extend(records)
        print(f" ✓ {filename}: {len(records)} months")

    df = pd.DataFrame(all_records)
    if df.empty:
        return df
    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    )
    return df.sort_values(["date", "platform"]).reset_index(drop=True)


# 5. Annual summary (online totals from 1099s + in person totals from the event log)

def build_annual_summary():
    online = [
        (2021, "ebay",      9149.72,  33, "eBay transactions PDF (33 orders, pre-vintage focus)"),
        (2022, "grailed",   7092.63,  49, "PayPal 1099-K"),
        (2022, "ebay",      1173.31,  10, "eBay 1099-K Oct-Dec only"),
        (2023, "ebay",      11250.29, 52, "eBay 1099-K"),
        (2023, "depop",     6013.02, 126, "Depop 1099-K"),
        (2023, "instagram", 2700.00,   1, "1985 Air Jordan 1 Chicago, direct sale"),
        (2024, "ebay",      7192.55,  88, "eBay 1099-K"),
        (2024, "depop",     10281.57, 215, "Depop 1099-K"),
        (2025, "ebay",      15609.53, 161, "eBay 1099-K"),
        (2025, "depop",     1912.08,  24, "Depop 1099-K"),
    ]
    df = pd.DataFrame(online, columns=["year", "platform", "gross_revenue", "num_transactions", "notes"])

    # In person totals are calculated from the market event log so the two sources can't disagree
    events = build_market_events()
    events = events[events["year"] <= 2025].copy()
    events["platform"] = "market"
    events.loc[events["event"] == "Instagram", "platform"] = "instagram"

    in_person = events.groupby(["year", "platform"], as_index=False).agg(
        gross_revenue=("richie_revenue", "sum")
    )
    in_person["num_transactions"] = None
    in_person["notes"] = "Summed from itemized market notes"

    df = pd.concat([df, in_person], ignore_index=True)
    df["num_transactions"] = df["num_transactions"].astype("Int64")
    return df.sort_values(["year", "platform"]).reset_index(drop=True)

# 6. Expenses (from Expenses 2024 PDF and 2025 business summary pdf)

def build_expenses():
    data = [
        (2024, "Cost of Goods (COG)",     4310.19),
        (2024, "Platform Fees",           2843.15),
        (2024, "Shipping",                2291.92),
        (2024, "Market Vendor Fees",      1898.00),
        (2024, "Misc (supplies/parking)",  416.83),
        (2025, "Cost of Goods (COG)",     7067.00),
        (2025, "Platform Fees",           2403.07),
        (2025, "Shipping",                1580.77),
        (2025, "Market Vendor Fees",      2345.00),
        (2025, "Misc (supplies/parking)",  259.30),
    ]
    return pd.DataFrame(data, columns=["year", "category", "amount"])

# 7. In person market events (daily totals, derived from itemized market notes)

def build_market_events():
    items = parse_market_notes()
    if items.empty:
        return pd.DataFrame()

    df = items.groupby(["date", "venue"], as_index=False).agg(
        items=("price", "count"),
        richie_revenue=("price", "sum"),
    )
    df = df.rename(columns={"venue": "event"})
    df["days"]  = df["event"].str.contains("weekend").map({True: 2, False: 1})
    df["year"]  = df["date"].dt.year
    df["month"] = df["date"].dt.month
    return df

# 8. Notable Items - manually curated, across platforms all years

def build_notable_items():
    data = [
        # (year, platform, item, cog, revenue)
        (2021, "ebay",      "Adidas Forum Bad Bunny Easter Egg",         160,  730.00),
        (2023, "ebay",      "Nike Dunk Low SB Cherry Stussy",            700, 1200.00),
        (2023, "ebay",      "New Balance 992 x JJJJound",                600,  875.00),
        (2023, "ebay",      "Nike Air Max 97 Sean Wotherspoon",          650,  849.99),
        (2023, "ebay",      "CPFM x Nike Air Force 1 White",             200,  549.99),
        (2023, "ebay",      "A Ma Maniere x Air Jordan 3",               400,  515.00),
        (2023, "ebay",      "Jordan 5 Retro Premio Bin23",               350,  500.00),
        (2023, "ebay",      "Nike Air Max 90 x Off-White",               250,  410.00),
        (2023, "ebay",      "Vintage Carhartt Detroit Jacket (Savers)",   15,  348.30),
        (2023, "instagram", "1985 Air Jordan 1 Chicago High",           1600, 2700.00),
        (2025, "market",    "LL Bean Two Way Tote",                      365, 1200.00),
        (2025, "market",    "1940s Levi's 506xx Type 1 Jacket",          100, 5000.00),
    ]
    df = pd.DataFrame(data, columns=["year", "platform", "item", "cog", "revenue"])
    df["profit"]  = df["revenue"] - df["cog"]
    df["roi_pct"] = (df["profit"] / df["cog"]) * 100
    return df


# 9. In person market notes (item level sales from handwritten notes)

VENUES = [
    ("instagram", "Instagram"),
    ("brimfield", "Brimfield"),
    ("select", "Select Markets"),
    ("bow", "Bow Vintage"),
    ("uml", "UML Event"),
    ("boutique", "BS Boutique"),
    ("downtown", "Downtown Crossing"),
    ("fenway", "Fenway Flea"),
    ("found", "Found"),
]
VENUE_OVERRIDES = {"2025-12-13": "Instagram"}
UNRECORDED_TOTALS = {"2025-05-13": 8500}        # Brimfield: day total know, most items not logged

DATE_RE     = re.compile(r"(\d{1,2})/(\d{1,2})(?:/(\d{2}))?")
PRICE_FIRST = re.compile(r"^\$?(\d+(?:\.\d+)?)\s*[-–—]?\s*(.*)$")    # "25 - blue shorts"
PRICE_LAST  = re.compile(r"^(.*?)\s*[-–—]\s*\$?(\d+(?:\.\d+)?)$")    # "Blue shorts- 25"
PARTNER_RE  = re.compile(r"^(daniel|christian|john)( sales)?[\s—–-]*$", re.IGNORECASE)
MINE_RE     = re.compile(r"^(my sales|me|richie)[\s—–-]*$", re.IGNORECASE)
SKIP_RE     = re.compile(r"^(notable sales|maybe\b|\d+\s+(pieces|tops|bottoms)$)", re.IGNORECASE)

def _is_header(line):
    starts_with_price = line.lstrip("$")[:1].isdigit() and not DATE_RE.match(line)
    return bool(DATE_RE.search(line)) and not starts_with_price and not PRICE_LAST.match(line)


def _parse_header(line, last_year):
    m = DATE_RE.search(line)
    year = int("20" + m.group(3)) if m.group(3) else last_year
    date = f"{year}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    low = line.lower()
    if "found" in low and "fenway" in low:
        venue = "Found + Fenway (weekend)"
    else:
        venue = next((name for key, name in VENUES if key in low), "Market")
    return date, VENUE_OVERRIDES.get(date, venue), year


def parse_market_notes():
    path = RAW / "In Person Market Sales Data.pdf"
    if not path.exists():
        print("  [SKIP] In Person Market Sales Data.pdf")
        return pd.DataFrame()

    with pdfplumber.open(path) as pdf:
        lines = [l.strip() for page in pdf.pages for l in (page.extract_text() or "").splitlines()]

    rows, skipped = [], []
    date = venue = None
    year, seller = 2024, "richie"

    for line in lines:
        if not line:
            continue
        low = line.lower()

        # 1. A new market heading resets the date, venue, and seller
        if _is_header(line):
            date, venue, year = _parse_header(line, year)
            seller = "richie"
            continue
        if low.startswith("day 2"):
            date = (pd.Timestamp(date) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            continue

        # 2. Section markers switch whose sales we're reading
        if PARTNER_RE.match(line):
            seller = "partner"
            continue
        if MINE_RE.match(line):
            seller = "richie"
            continue

        # 3. Skip totals, expenses (lines starting with "-"), and notes
        if "total" in low or line.startswith("-") or SKIP_RE.match(line):
            skipped.append(line)
            continue

        # 4. Item lines come in two formats: price first, or price last
        first, last = PRICE_FIRST.match(line), PRICE_LAST.match(line)
        if first and line.lstrip("$")[:1].isdigit():
            price, item = float(first.group(1)), first.group(2)
        elif last:
            item, price = last.group(1), float(last.group(2))
        else:
            skipped.append(line)
            continue

        if seller == "richie":
            rows.append({"date": date, "venue": venue, "price": price,
                         "item": item.strip(" -–—") or None})

    df = pd.DataFrame(rows)

    # Days where the total was known but individual sales weren't logged
    for d, total in UNRECORDED_TOTALS.items():
        day = df[df["date"] == d]
        filler = {"date": d, "venue": day["venue"].iloc[0],
                  "price": total - day["price"].sum(),
                  "item": "Unrecorded sales (too busy to log individually)"}
        df = pd.concat([df, pd.DataFrame([filler])], ignore_index=True)

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date", kind="stable").reset_index(drop=True)
    print(f"  ✓ Market notes: {len(df)} items across {df['date'].nunique()} dates "
          f"({len(skipped)} non-item lines skipped)")
    return df

# MAIN --------------------------------

if __name__ == "__main__":
    print("\n-- 2022 Flyp CSV exports--")
    items_df = parse_item_csvs()
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

    print("\n── 1099-K PDFs ──")
    monthly_df = parse_1099s()
    if not monthly_df.empty:
        monthly_df.to_csv(OUT / "monthly_revenue.csv", index=False)

    print("\n── Annual summary ──")
    annual_df = build_annual_summary()
    annual_df.to_csv(OUT / "annual_summary.csv", index=False)

    print("\n── Expenses ──")
    expenses_df = build_expenses()
    expenses_df.to_csv(OUT / "expenses.csv", index=False)

    print("\n── Market events ──")
    market_df = build_market_events()
    market_df.to_csv(OUT / "market_events.csv", index=False)

    print("\n── Market notes (item-level) ──")
    market_items_df = parse_market_notes()
    if not market_items_df.empty:
        market_items_df.to_csv(OUT / "market_items.csv", index=False)

    print("\n Done.\n")    