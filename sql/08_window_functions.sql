-- =====================================================================
-- 08_window_functions.sql  —  Vintage Resale Analytics
-- Rankings, running totals, year-over-year growth, and deciles
-- using window functions (OVER) and CTEs (WITH).
-- =====================================================================


-- 1. Year-over-year growth and running total
--    (matches the notebook's annual summary)
WITH yearly AS (
    SELECT year, SUM(gross_revenue) AS total
    FROM annual_summary
    GROUP BY year
),
with_previous AS (
    SELECT year,
           total,
           LAG(total) OVER (ORDER BY year)  AS previous_year,
           SUM(total) OVER (ORDER BY year)  AS running_total
    FROM yearly
)
SELECT year,
       total,
       previous_year,
       ROUND(100.0 * (total - previous_year) / previous_year, 1) AS yoy_growth_pct,
       running_total
FROM with_previous
ORDER BY year;


-- 2. Top 3 sales on each platform
WITH ranked AS (
    SELECT platform,
           sale_date,
           LEFT(item, 50) AS item,
           price,
           RANK() OVER (PARTITION BY platform ORDER BY price DESC) AS rank_in_platform
    FROM all_sales
    WHERE EXTRACT(YEAR FROM sale_date) <= 2025
)
SELECT platform, rank_in_platform, item, price, sale_date
FROM ranked
WHERE rank_in_platform <= 3
ORDER BY platform, rank_in_platform;


-- 3. Revenue by decile: how much do the top 10% of sales bring in?
--    (matches the notebook's "top 10% = 46%")
WITH deciles AS (
    SELECT price,
           NTILE(10) OVER (ORDER BY price DESC) AS decile
    FROM all_sales
    WHERE EXTRACT(YEAR FROM sale_date) <= 2025
),
by_decile AS (
    SELECT decile,
           COUNT(*)   AS sales,
           MIN(price) AS lowest_price,
           SUM(price) AS revenue
    FROM deciles
    GROUP BY decile
)
SELECT decile,
       sales,
       lowest_price,
       revenue,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 1)                    AS pct_of_revenue,
       ROUND(100.0 * SUM(revenue) OVER (ORDER BY decile) / SUM(revenue) OVER (), 1) AS cumulative_pct
FROM by_decile
ORDER BY decile;


-- 4. Each market day compared with that venue's average
SELECT sale_date,
       venue,
       sales,
       ROUND(AVG(sales) OVER (PARTITION BY venue), 2)          AS venue_avg,
       ROUND(sales - AVG(sales) OVER (PARTITION BY venue), 2)  AS vs_venue_avg,
       RANK() OVER (PARTITION BY venue ORDER BY sales DESC)    AS rank_at_venue
FROM market_days
WHERE venue IN ('Fenway Flea', 'Found', 'Select Markets')
ORDER BY venue, sale_date;


-- FINDINGS
-- * Year over year: -9.7% (2022), +141.5% (2023), +107.1% (2024), -24.3% (2025),
--   reaching $110,006 in total, the same as the notebook.
-- * The top 10% of sales (decile 1, every sale of $75+) brought in 46% of itemized revenue;
--   the bottom half of sales brought in about 20%.
-- * The #1 sale on each in-person channel (a $5,000 Levi's jacket, $2,250 in L.L.Bean totes)
--   is larger than the #1 sale on any online platform.
-- * Fenway Flea's best days were in June 2024; every 2025 Fenway day came in below the venue's
--   average, matching the drop in market activity in 2025.