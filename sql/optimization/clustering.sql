-- =============================================================================
-- CLUSTERING & PERFORMANCE OPTIMIZATION
-- Adventure Works Capstone Project
-- Purpose : Configure Snowflake cluster keys, search optimization,
--           result caching, and query-profile tuning recommendations.
-- =============================================================================

USE DATABASE ADVENTURE_WORKS_DB;

-- =============================================================================
-- 1. CLUSTER KEYS ON FACT TABLES
-- Rationale: Queries almost always filter on ORDER_DATE_KEY (range scans),
--            TERRITORY_KEY (region drill-downs), and PRODUCT_KEY (product analysis).
-- =============================================================================

-- FACT_SALES — cluster by date first, then territory, then product
ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_SALES
    CLUSTER BY (ORDER_DATE_KEY, TERRITORY_KEY, PRODUCT_KEY);

-- FACT_RETURNS — cluster by date and territory
ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_RETURNS
    CLUSTER BY (RETURN_DATE_KEY, TERRITORY_KEY);

-- SILVER_SALES — cluster to speed up GOLD layer CTAS refreshes
ALTER TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_SALES
    CLUSTER BY (ORDER_DATE, TERRITORY_KEY);

-- =============================================================================
-- 2. CLUSTER KEYS ON DIMENSION TABLES
-- Smaller tables rarely need clustering, but product and customer
-- benefit from category/segment-based micro-partitioning.
-- =============================================================================

ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT
    CLUSTER BY (CATEGORY_NAME, PRICE_TIER);

ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER
    CLUSTER BY (INCOME_BAND, OCCUPATION);

-- =============================================================================
-- 3. CHECK CLUSTERING DEPTH (AFTER DATA LOAD)
-- Run these after loading data to evaluate whether reclustering is needed.
-- =============================================================================
SELECT SYSTEM$CLUSTERING_DEPTH('ADVENTURE_WORKS_DB.GOLD.FACT_SALES');
SELECT SYSTEM$CLUSTERING_INFORMATION('ADVENTURE_WORKS_DB.GOLD.FACT_SALES',
    '(ORDER_DATE_KEY, TERRITORY_KEY, PRODUCT_KEY)');

SELECT SYSTEM$CLUSTERING_DEPTH('ADVENTURE_WORKS_DB.GOLD.FACT_RETURNS');
SELECT SYSTEM$CLUSTERING_INFORMATION('ADVENTURE_WORKS_DB.GOLD.FACT_RETURNS',
    '(RETURN_DATE_KEY, TERRITORY_KEY)');

-- =============================================================================
-- 4. SEARCH OPTIMIZATION SERVICE
-- Adds point-lookup acceleration for high-cardinality equality filters
-- (e.g., WHERE ORDER_NUMBER = 'SO12345').
-- =============================================================================
ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_SALES
    ADD SEARCH OPTIMIZATION ON EQUALITY(ORDER_NUMBER);

ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER
    ADD SEARCH OPTIMIZATION ON EQUALITY(EMAIL_ADDRESS, FULL_NAME);

ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT
    ADD SEARCH OPTIMIZATION ON EQUALITY(PRODUCT_SKU, PRODUCT_NAME);

-- =============================================================================
-- 5. WAREHOUSE SCALING STRATEGY
-- =============================================================================

-- Analytics warehouse (BI tool connections — Auto-scale for concurrency)
CREATE OR REPLACE WAREHOUSE CAPSTONE_ANALYTICS_WH
    WAREHOUSE_SIZE         = 'MEDIUM'
    AUTO_SUSPEND           = 120
    AUTO_RESUME            = TRUE
    MIN_CLUSTER_COUNT      = 1
    MAX_CLUSTER_COUNT      = 3
    SCALING_POLICY         = 'ECONOMY'
    COMMENT                = 'Multi-cluster warehouse for concurrent BI queries';

-- ETL warehouse (single-cluster, larger size for data loading transforms)
CREATE OR REPLACE WAREHOUSE CAPSTONE_ETL_WH
    WAREHOUSE_SIZE         = 'LARGE'
    AUTO_SUSPEND           = 60
    AUTO_RESUME            = TRUE
    MIN_CLUSTER_COUNT      = 1
    MAX_CLUSTER_COUNT      = 1
    COMMENT                = 'Dedicated ETL warehouse for heavy Bronze→Silver→Gold transforms';

-- =============================================================================
-- 6. RESULT CACHE — SESSION SETTINGS
-- Snowflake caches query results for 24 hours by default.
-- Verify it is enabled (should be TRUE by default).
-- =============================================================================
SHOW PARAMETERS LIKE 'USE_CACHED_RESULT' IN SESSION;
ALTER SESSION SET USE_CACHED_RESULT = TRUE;

-- =============================================================================
-- 7. QUERY PROFILE TIPS — NON-SQL GUIDANCE
-- (Comments for the assignment — not executable SQL)
--
-- a) USE_CACHED_RESULT=TRUE  -> 0-second repeat queries (test before presenting)
-- b) Avoid SELECT *           -> list only needed columns
-- c) Partition pruning        -> always filter on cluster key columns first
-- d) LIMIT on dev runs        -> LIMIT 1000 during development to avoid full scans
-- e) Semi-structured data     -> use FLATTEN/LATERAL for VARIANT columns
-- f) Spill to disk warnings   -> increase WH size if query profile shows "spilling"
-- g) Remote vs local spill    -> local spill is OK; remote spill = WH too small
-- h) Cartesian products       -> check EXPLAIN PLAN for missing join predicates
-- =============================================================================

-- =============================================================================
-- 8. MATERIALIZED VIEW FOR HEAVY AGGREGATION (Optional)
-- Useful if VW_MONTHLY_KPI is queried thousands of times per day by dashboards.
-- =============================================================================
CREATE OR REPLACE MATERIALIZED VIEW ADVENTURE_WORKS_DB.GOLD.MV_MONTHLY_REVENUE
COMMENT = 'Pre-aggregated monthly revenue — refreshed automatically by Snowflake'
AS
SELECT
    d.YEAR,
    d.MONTH_NUM,
    d.MONTH_NAME,
    ROUND(SUM(f.GROSS_REVENUE), 2) AS TOTAL_REVENUE,
    ROUND(SUM(f.GROSS_PROFIT),  2) AS TOTAL_PROFIT,
    COUNT(DISTINCT f.ORDER_NUMBER) AS TOTAL_ORDERS
FROM ADVENTURE_WORKS_DB.GOLD.FACT_SALES f
JOIN ADVENTURE_WORKS_DB.GOLD.DIM_DATE d ON f.ORDER_DATE_KEY = d.DATE_KEY
GROUP BY 1,2,3;

-- =============================================================================
-- 9. MONITORING — QUERY HISTORY & CREDIT USAGE
-- =============================================================================
-- Top 10 most expensive queries (last 7 days)
SELECT
    QUERY_ID,
    LEFT(QUERY_TEXT, 80)    AS QUERY_SNIPPET,
    TOTAL_ELAPSED_TIME / 1000 AS ELAPSED_SEC,
    BYTES_SCANNED / 1e9     AS GB_SCANNED,
    CREDITS_USED_CLOUD_SERVICES,
    WAREHOUSE_NAME,
    START_TIME
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
  AND EXECUTION_STATUS = 'SUCCESS'
ORDER BY TOTAL_ELAPSED_TIME DESC
LIMIT 10;

-- Credit consumption by warehouse
SELECT
    WAREHOUSE_NAME,
    SUM(CREDITS_USED)       AS TOTAL_CREDITS,
    SUM(CREDITS_USED_COMPUTE) AS COMPUTE_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD('month', -1, CURRENT_TIMESTAMP())
GROUP BY 1
ORDER BY 2 DESC;
