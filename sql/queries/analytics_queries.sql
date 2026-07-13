-- =============================================================================
-- ANALYTICS QUERIES
-- Adventure Works Capstone Project
-- Purpose : Business-facing SQL queries against the GOLD star schema.
--           Covers revenue, customers, products, returns, and trend analysis.
-- =============================================================================

USE DATABASE ADVENTURE_WORKS_DB;
USE SCHEMA   ADVENTURE_WORKS_DB.GOLD;

-- =============================================================================
-- 1. OVERALL SALES SUMMARY BY YEAR
-- =============================================================================
SELECT
    d.YEAR,
    COUNT(DISTINCT f.ORDER_NUMBER)          AS TOTAL_ORDERS,
    SUM(f.ORDER_QUANTITY)                   AS TOTAL_UNITS_SOLD,
    ROUND(SUM(f.GROSS_REVENUE),  2)         AS TOTAL_REVENUE,
    ROUND(SUM(f.GROSS_PROFIT),   2)         AS TOTAL_PROFIT,
    ROUND(AVG(f.MARGIN_PCT),     2)         AS AVG_MARGIN_PCT,
    ROUND(SUM(f.GROSS_REVENUE)
          / COUNT(DISTINCT f.ORDER_NUMBER), 2) AS AVG_ORDER_VALUE
FROM FACT_SALES f
JOIN DIM_DATE d ON f.ORDER_DATE_KEY = d.DATE_KEY
GROUP BY d.YEAR
ORDER BY d.YEAR;

-- =============================================================================
-- 2. MONTHLY REVENUE TREND (2020–2022)
-- =============================================================================
SELECT
    d.YEAR,
    d.MONTH_NUM,
    d.MONTH_NAME,
    ROUND(SUM(f.GROSS_REVENUE), 2)          AS MONTHLY_REVENUE,
    ROUND(SUM(f.GROSS_PROFIT),  2)          AS MONTHLY_PROFIT,
    LAG(SUM(f.GROSS_REVENUE)) OVER
        (ORDER BY d.YEAR, d.MONTH_NUM)      AS PREV_MONTH_REVENUE,
    ROUND((SUM(f.GROSS_REVENUE)
           - LAG(SUM(f.GROSS_REVENUE)) OVER (ORDER BY d.YEAR, d.MONTH_NUM))
          / NULLIF(LAG(SUM(f.GROSS_REVENUE)) OVER (ORDER BY d.YEAR, d.MONTH_NUM), 0)
          * 100, 2)                         AS MOM_GROWTH_PCT
FROM FACT_SALES f
JOIN DIM_DATE d ON f.ORDER_DATE_KEY = d.DATE_KEY
GROUP BY d.YEAR, d.MONTH_NUM, d.MONTH_NAME
ORDER BY d.YEAR, d.MONTH_NUM;

-- =============================================================================
-- 3. REVENUE BY PRODUCT CATEGORY & SUBCATEGORY
-- =============================================================================
SELECT
    p.CATEGORY_NAME,
    p.SUBCATEGORY_NAME,
    COUNT(DISTINCT f.ORDER_NUMBER)          AS TOTAL_ORDERS,
    SUM(f.ORDER_QUANTITY)                   AS UNITS_SOLD,
    ROUND(SUM(f.GROSS_REVENUE),  2)         AS TOTAL_REVENUE,
    ROUND(SUM(f.GROSS_PROFIT),   2)         AS TOTAL_PROFIT,
    ROUND(AVG(f.MARGIN_PCT),     2)         AS AVG_MARGIN_PCT
FROM FACT_SALES f
JOIN DIM_PRODUCT p ON f.PRODUCT_KEY = p.PRODUCT_KEY
GROUP BY p.CATEGORY_NAME, p.SUBCATEGORY_NAME
ORDER BY TOTAL_REVENUE DESC;

-- =============================================================================
-- 4. TOP 10 BEST-SELLING PRODUCTS
-- =============================================================================
SELECT
    p.PRODUCT_KEY,
    p.PRODUCT_NAME,
    p.CATEGORY_NAME,
    p.PRICE_TIER,
    SUM(f.ORDER_QUANTITY)                   AS UNITS_SOLD,
    ROUND(SUM(f.GROSS_REVENUE), 2)          AS TOTAL_REVENUE,
    ROUND(SUM(f.GROSS_PROFIT),  2)          AS TOTAL_PROFIT
FROM FACT_SALES f
JOIN DIM_PRODUCT p ON f.PRODUCT_KEY = p.PRODUCT_KEY
GROUP BY 1,2,3,4
ORDER BY UNITS_SOLD DESC
LIMIT 10;

-- =============================================================================
-- 5. CUSTOMER SEGMENTATION ANALYSIS
-- =============================================================================
SELECT
    c.INCOME_BAND,
    c.OCCUPATION,
    c.GENDER,
    c.MARITAL_STATUS,
    COUNT(DISTINCT c.CUSTOMER_KEY)          AS CUSTOMER_COUNT,
    COUNT(DISTINCT f.ORDER_NUMBER)          AS TOTAL_ORDERS,
    ROUND(SUM(f.GROSS_REVENUE), 2)          AS TOTAL_REVENUE,
    ROUND(SUM(f.GROSS_REVENUE)
          / COUNT(DISTINCT c.CUSTOMER_KEY), 2) AS REVENUE_PER_CUSTOMER
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.CUSTOMER_KEY = c.CUSTOMER_KEY
GROUP BY 1,2,3,4
ORDER BY REVENUE_PER_CUSTOMER DESC;

-- =============================================================================
-- 6. REVENUE BY GEOGRAPHY (TERRITORY)
-- =============================================================================
SELECT
    t.CONTINENT,
    t.COUNTRY,
    t.REGION,
    COUNT(DISTINCT f.ORDER_NUMBER)          AS TOTAL_ORDERS,
    ROUND(SUM(f.GROSS_REVENUE), 2)          AS TOTAL_REVENUE,
    ROUND(SUM(f.GROSS_PROFIT),  2)          AS TOTAL_PROFIT,
    ROUND(SUM(f.GROSS_REVENUE) * 100.0
          / SUM(SUM(f.GROSS_REVENUE)) OVER(), 2) AS REVENUE_SHARE_PCT
FROM FACT_SALES f
JOIN DIM_TERRITORY t ON f.TERRITORY_KEY = t.TERRITORY_KEY
GROUP BY 1,2,3
ORDER BY TOTAL_REVENUE DESC;

-- =============================================================================
-- 7. RETURN RATE BY PRODUCT (UNITS RETURNED vs UNITS SOLD)
-- =============================================================================
SELECT
    p.PRODUCT_NAME,
    p.CATEGORY_NAME,
    SUM(f.ORDER_QUANTITY)                   AS UNITS_SOLD,
    COALESCE(SUM(r.RETURN_QUANTITY), 0)     AS UNITS_RETURNED,
    ROUND(COALESCE(SUM(r.RETURN_QUANTITY), 0)
          / NULLIF(SUM(f.ORDER_QUANTITY), 0) * 100, 2) AS RETURN_RATE_PCT,
    ROUND(COALESCE(SUM(r.RETURN_REVENUE_IMPACT), 0), 2) AS RETURN_REVENUE_IMPACT
FROM FACT_SALES f
JOIN DIM_PRODUCT p ON f.PRODUCT_KEY = p.PRODUCT_KEY
LEFT JOIN FACT_RETURNS r ON f.PRODUCT_KEY = r.PRODUCT_KEY
GROUP BY 1,2
HAVING UNITS_SOLD > 0
ORDER BY RETURN_RATE_PCT DESC
LIMIT 20;

-- =============================================================================
-- 8. QUARTERLY REVENUE WITH YoY COMPARISON
-- =============================================================================
WITH quarterly AS (
    SELECT
        d.YEAR,
        d.QUARTER_NAME,
        d.QUARTER_NUM,
        ROUND(SUM(f.GROSS_REVENUE), 2) AS QUARTERLY_REVENUE
    FROM FACT_SALES f
    JOIN DIM_DATE d ON f.ORDER_DATE_KEY = d.DATE_KEY
    GROUP BY 1,2,3
)
SELECT
    YEAR,
    QUARTER_NAME,
    QUARTERLY_REVENUE,
    LAG(QUARTERLY_REVENUE) OVER
        (PARTITION BY QUARTER_NUM ORDER BY YEAR) AS PREV_YEAR_REVENUE,
    ROUND((QUARTERLY_REVENUE
           - LAG(QUARTERLY_REVENUE) OVER (PARTITION BY QUARTER_NUM ORDER BY YEAR))
          / NULLIF(LAG(QUARTERLY_REVENUE) OVER (PARTITION BY QUARTER_NUM ORDER BY YEAR), 0)
          * 100, 2) AS YOY_GROWTH_PCT
FROM quarterly
ORDER BY YEAR, QUARTER_NUM;

-- =============================================================================
-- 9. CUSTOMER LIFETIME VALUE (CLV) — TOP 20
-- =============================================================================
SELECT
    c.CUSTOMER_KEY,
    c.FULL_NAME,
    c.OCCUPATION,
    c.INCOME_BAND,
    MIN(f.ORDER_DATE_KEY)                   AS FIRST_ORDER_DATE,
    MAX(f.ORDER_DATE_KEY)                   AS LAST_ORDER_DATE,
    COUNT(DISTINCT f.ORDER_NUMBER)          AS TOTAL_ORDERS,
    SUM(f.ORDER_QUANTITY)                   AS TOTAL_UNITS,
    ROUND(SUM(f.GROSS_REVENUE), 2)          AS LIFETIME_REVENUE,
    ROUND(SUM(f.GROSS_PROFIT),  2)          AS LIFETIME_PROFIT,
    ROUND(SUM(f.GROSS_REVENUE)
          / COUNT(DISTINCT f.ORDER_NUMBER), 2) AS AVG_ORDER_VALUE
FROM FACT_SALES f
JOIN DIM_CUSTOMER c ON f.CUSTOMER_KEY = c.CUSTOMER_KEY
GROUP BY 1,2,3,4
ORDER BY LIFETIME_REVENUE DESC
LIMIT 20;

-- =============================================================================
-- 10. PRODUCT CATEGORY SALES UNPIVOT ANALYSIS
-- =============================================================================
SELECT
    SALE_DATE,
    PRODUCT_CATEGORY,
    SUM(CASE WHEN REGION = 'North'   THEN SALES_AMOUNT ELSE 0 END) AS NORTH,
    SUM(CASE WHEN REGION = 'Central' THEN SALES_AMOUNT ELSE 0 END) AS CENTRAL,
    SUM(CASE WHEN REGION = 'South'   THEN SALES_AMOUNT ELSE 0 END) AS SOUTH,
    SUM(SALES_AMOUNT)                       AS TOTAL
FROM ADVENTURE_WORKS_DB.SILVER.SILVER_CATEGORY_SALES_UNPIVOT
GROUP BY 1,2
ORDER BY SALE_DATE, PRODUCT_CATEGORY;

-- =============================================================================
-- 11. WEEKEND vs WEEKDAY SALES PATTERN
-- =============================================================================
SELECT
    d.IS_WEEKEND,
    IFF(d.IS_WEEKEND, 'Weekend', 'Weekday')  AS DAY_TYPE,
    COUNT(DISTINCT f.ORDER_NUMBER)            AS TOTAL_ORDERS,
    ROUND(SUM(f.GROSS_REVENUE), 2)            AS TOTAL_REVENUE,
    ROUND(AVG(f.GROSS_REVENUE), 2)            AS AVG_ORDER_REVENUE
FROM FACT_SALES f
JOIN DIM_DATE d ON f.ORDER_DATE_KEY = d.DATE_KEY
GROUP BY 1,2
ORDER BY 1;

-- =============================================================================
-- 12. RUNNING CUMULATIVE REVENUE BY YEAR
-- =============================================================================
SELECT
    d.YEAR,
    d.MONTH_NUM,
    d.MONTH_NAME,
    ROUND(SUM(f.GROSS_REVENUE), 2)          AS MONTHLY_REVENUE,
    ROUND(SUM(SUM(f.GROSS_REVENUE)) OVER
        (PARTITION BY d.YEAR ORDER BY d.MONTH_NUM
         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS YTD_REVENUE
FROM FACT_SALES f
JOIN DIM_DATE d ON f.ORDER_DATE_KEY = d.DATE_KEY
GROUP BY d.YEAR, d.MONTH_NUM, d.MONTH_NAME
ORDER BY d.YEAR, d.MONTH_NUM;
