-- =====================================================================
-- 07_days_to_sell.sql  —  Vintage Resale Analytics
-- How long does inventory take to sell?
--   * Depop: listing date → sale date (342 sales, 2023–2025)
--   * 2022 Flyp items: purchase date → sale date (53 items with known cost)
-- =====================================================================

-- 1. Depop overall: how fast do listings sell?
SELECT COUNT(*)                                        AS sales,
       ROUND(AVG(sold_date - listed_date), 1)          AS avg_days,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sold_date - listed_date) AS median_days,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sold_date - listed_date <= 7)  / COUNT(*)) AS pct_within_week,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sold_date - listed_date <= 30) / COUNT(*)) AS pct_within_month,
       ROUND(100.0 * COUNT(*) FILTER (WHERE sold_date - listed_date > 90)  / COUNT(*)) AS pct_over_90_days
FROM depop_sales;


-- 2. Depop: sales grouped by how long they took
SELECT
    CASE
        WHEN sold_date - listed_date <= 7  THEN '1. Within a week'
        WHEN sold_date - listed_date <= 30 THEN '2. 8–30 days'
        WHEN sold_date - listed_date <= 90 THEN '3. 31–90 days'
        ELSE                                    '4. Over 90 days'
    END                      AS time_to_sell,
    COUNT(*)                 AS sales,
    ROUND(AVG(revenue), 2)   AS avg_price
FROM depop_sales
GROUP BY time_to_sell
ORDER BY time_to_sell;


-- 3. Depop: do cheaper items sell faster?
SELECT
    CASE
        WHEN revenue < 25 THEN '1. Under $25'
        WHEN revenue < 40 THEN '2. $25–39'
        WHEN revenue < 60 THEN '3. $40–59'
        ELSE                   '4. $60+'
    END        AS price_band,
    COUNT(*)   AS sales,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sold_date - listed_date) AS median_days
FROM depop_sales
GROUP BY price_band
ORDER BY price_band;


-- 4. Depop: which categories sell fastest? (categories with 10+ sales)
SELECT category,
       COUNT(*)               AS sales,
       ROUND(AVG(revenue), 2) AS avg_price,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sold_date - listed_date) AS median_days
FROM depop_sales
GROUP BY category
HAVING COUNT(*) >= 10
ORDER BY median_days;


-- 5. 2022: how long was inventory held from purchase to sale?
SELECT COUNT(*) AS items,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sold_date::DATE - purchase_date::DATE) AS median_days_held,
       ROUND(AVG(sold_date::DATE - purchase_date::DATE)) AS avg_days_held
FROM items_2022
WHERE cog IS NOT NULL;


-- 6. 2022: did items held longer earn more?
SELECT
    CASE
        WHEN sold_date::DATE - purchase_date::DATE <= 30  THEN '1. Sold within 30 days'
        WHEN sold_date::DATE - purchase_date::DATE <= 180 THEN '2. 31–180 days'
        ELSE                                                   '3. Over 180 days'
    END                                   AS holding_period,
    COUNT(*)                              AS items,
    ROUND(SUM(profit) / SUM(cog) * 100, 1) AS roi_pct,
    SUM(profit)                           AS total_profit
FROM items_2022
WHERE cog IS NOT NULL
GROUP BY holding_period
ORDER BY holding_period;


-- FINDINGS
-- * Depop listings sold fast: median 8.5 days. 46% sold within a week and 79% within a month.
--   The average (28 days) is much higher because 10% of items sat for 90+ days.
-- * Cheaper isn't faster. Items priced $25–59 sold in a median 7 days; items under $25
--   took 18 days. Low prices didn't make weak items sell, which supports moving them to markets.
-- * Bottoms (Depop's biggest category) sold fastest (7 days); tops took 18.
-- * 2022 inventory was held a median 48 days before selling. Items held 180+ days returned
--   45% ROI vs ~14% for faster sales, possibly from waiting for the right buyer, but the
--   group is small (14 items).
-- * Caveat: this data only includes items that SOLD. Inventory that never sold isn't recorded,
--   so true time to sell across all inventory is longer than shown.