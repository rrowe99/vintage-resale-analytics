-- =====================================================================
-- 02_load_and_verify.sql  —  Vintage Resale Analytics
--
-- Loading: each CSV in data/processed/ was imported into its matching
-- table with pgAdmin (Import/Export Data → Import, CSV, Header ON,
-- Encoding UTF8), excluding the auto-numbered ID column.
--
-- psql equivalent (run from the project root):
--   \copy annual_summary  FROM 'data/processed/annual_summary.csv'  CSV HEADER
--   \copy monthly_revenue FROM 'data/processed/monthly_revenue.csv' CSV HEADER
--   \copy expenses        FROM 'data/processed/expenses.csv'        CSV HEADER
--   \copy ebay_transactions (name, platform, cog, revenue, item_subtotal, shipping_charged,
--         platform_fee, net_payout, sold_date, sold_year, sold_month)
--         FROM 'data/processed/ebay_transactions.csv' CSV HEADER
--   \copy depop_sales (name, platform, cog, revenue, shipping_rev, usps_cost,
--         platform_fee, net_payout, sold_date, sold_year, sold_month)
--         FROM 'data/processed/depop_sales.csv' CSV HEADER
--   \copy items_2022 (name, brand, condition, cog, revenue, profit, roi_pct, platform,
--         sold_date, purchase_date, sold_year, sold_month)
--         FROM 'data/processed/items_2022.csv' CSV HEADER
--   \copy market_items (sale_date, venue, price, item)
--         FROM 'data/processed/market_items.csv' CSV HEADER
-- =====================================================================


-- Verify: row counts and dollar totals should match the CSVs / notebook
SELECT 'ebay_transactions' AS table_name, COUNT(*) AS row_count, SUM(revenue)       AS total FROM ebay_transactions
UNION ALL
SELECT 'depop_sales',                     COUNT(*),              SUM(revenue)                FROM depop_sales
UNION ALL
SELECT 'items_2022',                      COUNT(*),              SUM(revenue)                FROM items_2022
UNION ALL
SELECT 'market_items',                    COUNT(*),              SUM(price)                  FROM market_items
UNION ALL
SELECT 'monthly_revenue',                 COUNT(*),              SUM(gross_revenue)          FROM monthly_revenue
UNION ALL
SELECT 'annual_summary',                  COUNT(*),              SUM(gross_revenue)          FROM annual_summary
UNION ALL
SELECT 'expenses',                        COUNT(*),              SUM(amount)                 FROM expenses;