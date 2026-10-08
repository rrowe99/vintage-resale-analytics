-- =====================================================================
-- 01_schema.sql  —  Vintage Resale Analytics
-- Creates the tables for the resale database.
-- Safe to re-run: drops existing tables first.
-- =====================================================================

DROP TABLE IF EXISTS market_items, items_2022, depop_sales,
ebay_transactions, monthly_revenue, annual_summary, expenses, platforms CASCADE;

-- Lookup table: every sales channel, and whether it's online or in person

CREATE TABLE platforms (
    platform    VARCHAR(20) PRIMARY KEY,
    display_name    VARCHAR(30) NOT NULL,
    channel         VARCHAR(10) NOT NULL CHECK (channel IN ('online', 'in_person'))
);

INSERT INTO platforms(platform, display_name, channel)
VALUES
('ebay', 'eBay', 'online'),
('depop', 'Depop', 'online'),
('grailed', 'Grailed', 'online'),
('instagram', 'Instagram', 'in_person'),
('market', 'Market', 'in_person');

--Annual and monthly totals (from 1099-K forms and the market notes)

CREATE TABLE annual_summary (
    year    SMALLINT    NOT NULL,
    platform    VARCHAR(20) NOT NULL REFERENCES platforms(platform),
    gross_revenue   NUMERIC(10,2)   NOT NULL CHECK (gross_revenue >= 0),
    num_transactions    INTEGER     CHECK (num_transactions >= 0),
    notes   TEXT,
    PRIMARY KEY(year, platform)
);

CREATE TABLE monthly_revenue (
    year    SMALLINT    NOT NULL,
    month   SMALLINT    NOT NULL CHECK(month BETWEEN 1 AND 12),
    platform    SMALLCHAR(20)   NOT NULL REFERENCES platforms (platform),
    gross_revenue   NUMERIC(10,2)   NOT NULL CHECK(gross_revenue > 0),
    month_start     DATE    NOT NULL,
    PRIMARY KEY (year, month, platform)
);

CREATE TABLE expenses (
    year SMALLINT   NOT NULL,
    category    VARCHAR(40) NOT NULL,
    amount  NUMERIC(10,2)   NOT NULL CHECK (amount >= 0),
    PRIMARY KEY (year, category)
);

-- Individual sales

CREATE TABLE ebay_transactions (
    sale_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(150)    NOT NULL,
    platform    VARCHAR(20)     NOT NULL REFERENCES platforms (platform),
    category    NUMERIC(10,2),
    revenue     NUMERIC(10,2)   NOT NULL CHECK (revenue > 0),
    item_subtotal   NUMERIC(10,2)   NOT NULL,
    shipping_charged    NUMERIC(10,2)   NOT NULL,
    platform_fee    NUMERIC(10,2)   NOT NULL CHECK (platform_fee >= 0),
    net_payout  NUMERIC(10,2)   NOT NULL,
    sold_date   DATE    NOT NULL,
    sold_year   SMALLINT    NOT NULL,
    sold_month  SMALLINT    NOT NULL
);

CREATE TABLE depop_transactions (
    sale_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(150)    NOT NULL,
    platform    VARCHAR(20) NOT NULL REFERENCES platforms (platform),
    cog         NUMERIC(10,2),
    revenue     NUMERIC(10,2) NOT NULL CHECK (revenue > 0),
    shipping_rev    NUMERIC(10,2) NOT NULL,
    usps_cost   NUMERIC(10,2) NOT NULL,
    platform_fee    NUMERIC(10,2) NOT NULL CHECK (platform_fee >= 0),
    net_payout      NUMERIC(10,2) NOT NULL,
    sold_date       DATE    NOT NULL,
    sold_year       SMALLINT    NOT NULL,
    sold_month      SMALLINT    NOT NULL
);

CREATE TABLE items_2022 (
    item_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        VARCHAR(150)    NOT NULL,
    brand       VARCHAR(50),
    condition   VARCHAR(20),
    cog         NUMERIC(10,2)   CHECK (cog >= 0),
    revenue     NUMERIC(10,2) NOT NULL CHECK (revenue > 0),
    profit      NUMERIC(10,2),
    roi_pct     NUMERIC(10,2),
    platform       VARCHAR(20)   NOT NULL REFERENCES platforms (platform),
    sold_date      TIMESTAMPTZ   NOT NULL,
    purchase_date  TIMESTAMPTZ,
    sold_year      SMALLINT      NOT NULL,
    sold_month     SMALLINT      NOT NULL
);

CREATE TABLE market_items (
    sale_id     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sale_date   DATE    NOT NULL,
    venue       VARCHAR(40) NOT NULL,
    price       NUMERIC(10,2) NOT NULL CHECK (price > 0),
    item        VARCHAR(150)
);
