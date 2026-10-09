-- =====================================================================
-- 05_views.sql  —  Vintage Resale Analytics
-- Reusable views built on top of the cleaned tables.
-- Safe to re-run.
-- =====================================================================

DROP VIEW IF EXISTS all_sales, market_days;

-- all_sales: every individually recorded sale, from every source, in one shape
CREATE VIEW all_sales AS
SELECT
    'ebay_transactions' AS source_table,
    platform,
    sold_date       AS sale_date,
    name            AS item,
    item_subtotal   AS price,
    NULL            AS venue
FROM ebay_transactions

UNION ALL

SELECT 'depop_sales', platform, sold_date, name, revenue, NULL
FROM depop_sales

UNION ALL

SELECT 'items_2022', platform, sold_date::DATE, name, revenue, NULL
FROM items_2022

UNION ALL

SELECT
    'market_items',
    CASE WHEN venue = 'Instagram' THEN 'instagram' ELSE 'market' END,
    sale_date,
    item,
    price,
    venue
FROM market_items
WHERE COALESCE(item, '') NOT LIKE 'Unrecorded%';

-- market_days one row per market day, calculated from itemized sales
-- (replaces the hand typed market log the project started with
CREATE VIEW market_days AS
SELECT
    sale_date,
    venue,
    COUNT(*)   AS entries,
    SUM(price) AS sales,
    CASE WHEN venue LIKE '%weekend%' THEN 2 ELSE 1 END AS days
FROM market_items
WHERE venue <> 'Instagram'
GROUP BY sale_date, venue;

-- Checks: these should match the notebook

-- Sales by platform (2021-2025)
SELECT platform, COUNT(*) AS sales, SUM(price) AS total
FROM all_sales
WHERE EXTRACT(YEAR FROM sale_date) <= 2025
GROUP BY platform
ORDER BY total DESC;

-- Grand total: notebook Q4 shows 1,461 sales and $70,224
SELECT COUNT(*) AS sales, SUM(price) AS total
FROM all_sales
WHERE EXTRACT(YEAR FROM sale_date) <= 2025;

-- Online vs in person, using the platforms lookup table
SELECT p.channel, COUNT(*) AS sales, SUM(a.price) AS total, ROUND(AVG(a.price), 2) AS avg_price
FROM all_sales AS a
JOIN platforms AS p ON a.platform = p.platform
WHERE EXTRACT(YEAR FROM a.sale_date) <= 2025
GROUP BY p.channel;

-- Market days by year: notebook Q3 shows 31 days / $23,861 in 2024
SELECT EXTRACT(YEAR FROM sale_date) AS year,
       SUM(days)                    AS market_days,
       SUM(sales)                   AS sales,
       ROUND(SUM(sales) / SUM(days), 2) AS sales_per_day
FROM market_days
GROUP BY year
ORDER BY year;