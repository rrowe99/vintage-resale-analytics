-- =====================================================================
-- 03_data_quality.sql  —  Vintage Resale Analytics
-- Checks the loaded data for common problems, then fixes the ones
-- that belong in the database. Run after 02 (loading).
-- Safe to re-run: every fix only changes rows that still need it.
-- =====================================================================



-- 1. Duplicate sales (same item, same day, same price)

SELECT 'ebay_transactions' AS table_name, COUNT(*) AS duplicate_groups
FROM (SELECT name, sold_date, revenue
      FROM ebay_transactions
      GROUP BY name, sold_date, revenue
      HAVING COUNT(*) > 1) AS d
UNION ALL
SELECT 'depop_sales', COUNT(*)
FROM (SELECT name, sold_date, revenue
      FROM depop_sales
      GROUP BY name, sold_date, revenue
      HAVING COUNT(*) > 1) AS d;

SELECT sold_date, LEFT(name, 50) AS name, revenue, COUNT(*) AS copies
FROM depop_sales
GROUP BY sold_date, name, revenue
HAVING COUNT(*) > 1
ORDER BY sold_date;
-- FINDING: 18 of the 19 groups fall between Dec 1–30, 2023. Two Depop
-- exports overlap ("10_01_2023 - 12_30_2023" and "12_01_2023 - 02_29_2024"),
-- so every December 2023 sale was loaded twice. The 2024-01-03 pair is two
-- real sales (7:43 AM and 7:53 PM in the raw export). Fixed in the Python
-- pipeline so both the notebook and the database get clean data.



-- 2. Missing values

SELECT
    COUNT(*)                               AS total_items,
    COUNT(*) FILTER (WHERE brand IS NULL)  AS missing_brand,
    COUNT(*) FILTER (WHERE roi_pct IS NULL) AS missing_roi,
    COUNT(*) FILTER (WHERE cog = 0)        AS zero_cost
FROM items_2022;

SELECT
    COUNT(*)                              AS total_sales,
    COUNT(*) FILTER (WHERE item IS NULL)  AS missing_description
FROM market_items;



-- 3. Cost of goods: 0 is a placeholder for "unknown", so make it NULL

SELECT 'ebay_transactions' AS table_name, COUNT(*) FILTER (WHERE cog = 0) AS zero_cog, COUNT(*) AS total
FROM ebay_transactions
UNION ALL
SELECT 'depop_sales', COUNT(*) FILTER (WHERE cog = 0), COUNT(*)
FROM depop_sales;

UPDATE ebay_transactions SET cog = NULL WHERE cog = 0;
UPDATE depop_sales       SET cog = NULL WHERE cog = 0;
UPDATE items_2022        SET cog = NULL, profit = NULL WHERE cog = 0;



-- 4. Inconsistent labels: 'Used', 'used', 'USed'

SELECT condition, COUNT(*) FROM items_2022 GROUP BY condition ORDER BY COUNT(*) DESC;

UPDATE items_2022 SET condition = INITCAP(condition);

SELECT condition, COUNT(*) FROM items_2022 GROUP BY condition ORDER BY COUNT(*) DESC;



-- 5. Extra spaces at the start or end of item names

SELECT 'items_2022' AS table_name, COUNT(*) FILTER (WHERE name <> TRIM(name)) AS untrimmed FROM items_2022
UNION ALL
SELECT 'ebay_transactions', COUNT(*) FILTER (WHERE name <> TRIM(name)) FROM ebay_transactions
UNION ALL
SELECT 'depop_sales',       COUNT(*) FILTER (WHERE name <> TRIM(name)) FROM depop_sales;

UPDATE items_2022        SET name = TRIM(name) WHERE name <> TRIM(name);
UPDATE ebay_transactions SET name = TRIM(name) WHERE name <> TRIM(name);
UPDATE depop_sales       SET name = TRIM(name) WHERE name <> TRIM(name);



-- 6. Sanity checks (should all return 0)

SELECT COUNT(*) AS bought_after_sold
FROM items_2022
WHERE purchase_date > sold_date;

SELECT COUNT(*) AS ebay_revenue_mismatch
FROM ebay_transactions
WHERE revenue <> item_subtotal + shipping_charged;