-- =====================================================================
-- 04_update_depop_and_reload.sql  —  Vintage Resale Analytics
-- Migration after the pipeline fix that removed duplicate and refunded
-- sales and added Depop listing date, brand, and category.
-- Safe to re-run.
-- =====================================================================

-- 1. Add the new Depop columns (IF NOT EXISTS makes this safe to re-run)
ALTER TABLE depop_sales
    ADD COLUMN IF NOT EXISTS listed_date DATE,
    ADD COLUMN IF NOT EXISTS brand       VARCHAR(50),
    ADD COLUMN IF NOT EXISTS category    VARCHAR(30);

-- 2. An item can't sell before it's listed
ALTER TABLE depop_sales DROP CONSTRAINT IF EXISTS listed_before_sold;
ALTER TABLE depop_sales ADD CONSTRAINT listed_before_sold CHECK (listed_date <= sold_date);

-- 3. Empty both tables so the corrected CSVs can be re-imported
TRUNCATE ebay_transactions, depop_sales RESTART IDENTITY;

-- Next steps (done in pgAdmin):
--   a. Import data/processed/ebay_transactions.csv and depop_sales.csv
--      (CSV, Header ON, UTF8, exclude sale_id)
--   b. Re-run sections 3 and 5 of 03_data_quality.sql
--   c. Re-run 02_load_and_verify.sql: expect 183 eBay and 342 Depop rows