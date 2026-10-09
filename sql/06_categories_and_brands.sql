-- =====================================================================
-- 06_categories_and_brands.sql  —  Vintage Resale Analytics
-- Tags every sale with a product category and brand using keyword rules,
-- then answers: what sells, for how much, and where?
-- =====================================================================

DROP VIEW IF EXISTS sales_tagged;

CREATE VIEW sales_tagged AS
SELECT  
    a.*,
    p.channel,
    CASE    
        WHEN item ILIKE ANY (ARRAY['%bundle%', '%pile'])    THEN 'Bundles & piles'
        WHEN item ILIKE ANY (ARRAY['% bag', '% bag %', '% bags%', '%tote%', '%purse%',
                                   '%backpack%', '%rucksack%', '%duffle%', '%messenger%'])   THEN 'Bags'
        WHEN item ILIKE ANY (ARRAY['%shoe%', '%sneaker%', '%boot%', '%dunk%', '%samba%',
                                   '%clog%', '%converse%', '%yeezy%', '%air max%', '%air force%',
                                   '%jordan%retro%', '%kobe%', '%skechers%', '%new balance%',
                                   '%ozweego%'])                                             THEN 'Footwear'
        WHEN item ILIKE ANY (ARRAY['%skirt%', '%dress%', '%slip%'])                          THEN 'Skirts & dresses'
        WHEN item ILIKE ANY (ARRAY['%jacket%', '%coat%', '%parka%', '%bomber%', '%vest%',
                                   '%windbreaker%', '%harrington%', '%chore%', '%trench%',
                                   '%puffer%', '%varsity%', '%leather%'])                    THEN 'Jackets & coats'
        WHEN item ILIKE ANY (ARRAY['%shorts%', '%jort%'])                                    THEN 'Shorts'
        WHEN item ILIKE ANY (ARRAY['%jean%', '%pant%', '%cargo%', '%carpenter%', '%dungaree%',
                                   '%flare%', '%khaki%', '%jogger%', '%overall%', '%sweats%',
                                   '%double knee%', '%og 107%'])                             THEN 'Jeans & pants'
        WHEN item ILIKE '%jersey%'                                                           THEN 'Jerseys'
        WHEN item ILIKE ANY (ARRAY['%hoodie%', '%sweatshirt%', '%crewneck%', '%crew neck%',
                                   '%zip%', '%pullover%', '%fleece%'])                       THEN 'Hoodies & sweatshirts'
        WHEN item ILIKE ANY (ARRAY['%sweater%', '%knit%', '%cardigan%', '%turtleneck%'])     THEN 'Sweaters & knits'
        WHEN item ILIKE ANY (ARRAY['%tee%', '%shirt%', '%top%', '%tank%', '%polo%', '%rugby%',
                                   '%thermal%', '%sleeve%', '%blouse%', '%corset%', '%lace%',
                                   '%button%', '%ringer%', '%crew%'])                        THEN 'Tops & tees'
        WHEN item ILIKE ANY (ARRAY['hat%', '% hat%', '%cap %', '%beanie%', '%belt%'])        THEN 'Hats & accessories'
        ELSE 'Other / unspecified'
    END AS category,
    CASE
        WHEN item ILIKE ANY (ARRAY['%ll bean%', '%l.l. bean%', '%l.l.bean%', '% bean %'])    THEN 'L.L.Bean'
        WHEN item ILIKE '%carhartt%'                                                         THEN 'Carhartt'
        WHEN item ILIKE '%harley%'                                                           THEN 'Harley-Davidson'
        WHEN item ILIKE '%levi%'                                                             THEN 'Levi''s'
        WHEN item ILIKE ANY (ARRAY['%red sox%', '%patriots%', '%celtics%', '%bruins%'])      THEN 'Boston sports'
        WHEN item ILIKE '%affliction%'                                                       THEN 'Affliction'
        WHEN item ILIKE ANY (ARRAY['%ralph lauren%', '%polo sport%', '%polo jeans%'])        THEN 'Ralph Lauren'
        WHEN item ILIKE ANY (ARRAY['%nike%', '%jordan%retro%', '%dunk%'])                    THEN 'Nike'
        WHEN item ILIKE '%dickies%'                                                          THEN 'Dickies'
        WHEN item ILIKE '%coach%'                                                            THEN 'Coach'
        WHEN item ILIKE '%southpole%'                                                        THEN 'Southpole'
        WHEN item ILIKE '%nascar%'                                                           THEN 'NASCAR'
        WHEN item ILIKE '%adidas%'                                                           THEN 'Adidas'
        ELSE NULL
    END AS brand
FROM all_sales AS a
JOIN platforms AS p ON a.platform = p.platform
WHERE EXTRACT(YEAR FROM a.sale_date) <= 2025;

--1. Which categories bring in the most money?
SELECT category,
    COUNT(*)    AS sales,
    SUM(price)  AS revenue,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price)::NUMERIC, 2) AS median_price
FROM sales_tagged
GROUP BY category
ORDER BY revenue DESC;

--2. Where does each category sell: online or in person?
SELECT category,
    COUNT(*)        AS sales,
    COUNT(*) FILTER (WHERE channel = 'online')  AS online,
    COUNT(*) FILTER (WHERE channel = 'in_person')   AS in_person,
    ROUND(100.0 * COUNT(*) FILTER (WHERE channel = 'in_person') / COUNT(*)) AS pct_in_person
FROM sales_tagged
GROUP BY category
ORDER BY sales DESC;

-- 3. Which brands bring in the most money?
SELECT brand,
    COUNT(*)    AS sales,
    SUM(price)  AS revenue,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price)::NUMERIC, 2) AS median_price,
    MAX(price)  AS best_sale
FROM sales_tagged
WHERE brand IS NOT NULL
GROUP BY brand
ORDER BY revenue DESC;

-- 4. Where mdoes Boston sports gear sell?
SELECT COALESCE(venue, platform) AS sold_at,
       COUNT(*)   AS sales,
       SUM(price) AS revenue
FROM sales_tagged
WHERE brand = 'Boston sports'
GROUP BY sold_at
ORDER BY sales DESC;

-- 5. How much of the data could be tagged?
SELECT COUNT(*)     AS total_sales,
    COUNT(*) FILTER (WHERE category <> 'Other / unspecified')   AS with_category,
    COUNT(brand)    AS with_brand
FROM sales_tagged


-- FINDINGS
-- * Jackets & coats bring in the most revenue ($16.6k, median $50), and 65% sell in person.
-- * Jeans & pants are the most-sold category (304 sales), mostly online (Depop baggy jeans).
-- * Footwear sells almost entirely online (92%) at the highest median price ($75).
-- * Tops & tees: 290 sales but a $20 median, 77% sold in person. Low-price items go to markets.
-- * Levi's, Nike, and L.L.Bean lead brand revenue; Levi's and L.L.Bean are driven by a few big sales.
-- * Boston sports gear is the most-sold brand group (84 sales); 55% of it sold at Fenway Flea.