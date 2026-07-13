-- =============================================================================
-- DYNAMIC DATA MASKING POLICIES
-- Adventure Works Capstone Project
-- Purpose : Protect PII columns (email, name, income) based on the
--           caller's role. Data Engineers see real values; Analysts
--           see partially masked values; Viewers see fully masked values.
-- =============================================================================

USE DATABASE ADVENTURE_WORKS_DB;
USE SCHEMA   ADVENTURE_WORKS_DB.GOLD;

-- =============================================================================
-- 1. EMAIL ADDRESS MASKING
-- Engineer  : full email
-- Analyst   : first char + '***' + @domain  (j***@adventure-works.com)
-- Viewer    : fully masked  (***@***.com)
-- =============================================================================
CREATE OR REPLACE MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_EMAIL_ADDRESS
    AS (VAL VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('CAPSTONE_SYSADMIN', 'CAPSTONE_DATA_ENGINEER')
            THEN VAL
        WHEN CURRENT_ROLE() = 'CAPSTONE_ANALYST'
            THEN LEFT(VAL, 1) || '***@' || SPLIT_PART(VAL, '@', 2)
        ELSE
            '***@***.com'
    END;

-- Apply to DIM_CUSTOMER
ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER
    MODIFY COLUMN EMAIL_ADDRESS
    SET MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_EMAIL_ADDRESS;

-- Apply to SILVER_CUSTOMER
ALTER TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_CUSTOMER
    MODIFY COLUMN EMAIL_ADDRESS
    SET MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_EMAIL_ADDRESS;

-- =============================================================================
-- 2. FULL NAME MASKING
-- Engineer  : full name (Jon Yang)
-- Analyst   : first name + last initial  (Jon Y.)
-- Viewer    : initials only  (J.Y.)
-- =============================================================================
CREATE OR REPLACE MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_FULL_NAME
    AS (VAL VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('CAPSTONE_SYSADMIN', 'CAPSTONE_DATA_ENGINEER')
            THEN VAL
        WHEN CURRENT_ROLE() = 'CAPSTONE_ANALYST'
            THEN SPLIT_PART(VAL, ' ', 1)
                 || ' ' || LEFT(SPLIT_PART(VAL, ' ', 2), 1) || '.'
        ELSE
            LEFT(SPLIT_PART(VAL, ' ', 1), 1) || '.'
            || LEFT(SPLIT_PART(VAL, ' ', 2), 1) || '.'
    END;

ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER
    MODIFY COLUMN FULL_NAME
    SET MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_FULL_NAME;

-- =============================================================================
-- 3. ANNUAL INCOME MASKING
-- Engineer  : exact value
-- Analyst   : rounded to nearest $10,000
-- Viewer    : replaced with income band label
-- =============================================================================
CREATE OR REPLACE MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_ANNUAL_INCOME
    AS (VAL NUMBER) RETURNS NUMBER ->
    CASE
        WHEN CURRENT_ROLE() IN ('CAPSTONE_SYSADMIN', 'CAPSTONE_DATA_ENGINEER')
            THEN VAL
        WHEN CURRENT_ROLE() = 'CAPSTONE_ANALYST'
            THEN ROUND(VAL, -4)   -- round to nearest 10,000
        ELSE
            0                     -- viewers see 0 (income band column is visible)
    END;

ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER
    MODIFY COLUMN ANNUAL_INCOME
    SET MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_ANNUAL_INCOME;

-- =============================================================================
-- 4. BIRTH DATE MASKING
-- Engineer  : full date (1966-04-08)
-- Analyst   : year only  (1966-01-01)
-- Viewer    : NULL
-- =============================================================================
CREATE OR REPLACE MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_BIRTH_DATE
    AS (VAL DATE) RETURNS DATE ->
    CASE
        WHEN CURRENT_ROLE() IN ('CAPSTONE_SYSADMIN', 'CAPSTONE_DATA_ENGINEER')
            THEN VAL
        WHEN CURRENT_ROLE() = 'CAPSTONE_ANALYST'
            THEN DATE_TRUNC('year', VAL)::DATE
        ELSE
            NULL
    END;

ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER
    MODIFY COLUMN BIRTH_DATE
    SET MASKING POLICY ADVENTURE_WORKS_DB.GOLD.MASK_BIRTH_DATE;

-- =============================================================================
-- 5. ROW ACCESS POLICY — Territory-scoped data access
-- Viewers can only see rows for their assigned territory.
-- Analysts and Engineers see all rows.
-- (Requires a mapping table; shown conceptually here.)
-- =============================================================================

-- Mapping table: user → allowed territory keys
CREATE TABLE IF NOT EXISTS ADVENTURE_WORKS_DB.GOLD.USER_TERRITORY_ACCESS (
    USER_NAME       VARCHAR(100) NOT NULL,
    TERRITORY_KEY   NUMBER       NOT NULL
);

-- Sample mappings (adjust to real usernames)
INSERT INTO ADVENTURE_WORKS_DB.GOLD.USER_TERRITORY_ACCESS VALUES
    ('VIEWER_USER', 1),
    ('VIEWER_USER', 2),
    ('VIEWER_USER', 3);

CREATE OR REPLACE ROW ACCESS POLICY ADVENTURE_WORKS_DB.GOLD.RAP_TERRITORY_FILTER
    AS (territory_key NUMBER) RETURNS BOOLEAN ->
    CASE
        WHEN CURRENT_ROLE() IN ('CAPSTONE_SYSADMIN', 'CAPSTONE_DATA_ENGINEER',
                                 'CAPSTONE_ANALYST')
            THEN TRUE
        ELSE
            EXISTS (
                SELECT 1
                FROM ADVENTURE_WORKS_DB.GOLD.USER_TERRITORY_ACCESS
                WHERE USER_NAME    = CURRENT_USER()
                  AND TERRITORY_KEY = territory_key
            )
    END;

ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_SALES
    ADD ROW ACCESS POLICY ADVENTURE_WORKS_DB.GOLD.RAP_TERRITORY_FILTER ON (TERRITORY_KEY);

-- =============================================================================
-- 6. VERIFY POLICIES
-- =============================================================================
SHOW MASKING POLICIES IN SCHEMA ADVENTURE_WORKS_DB.GOLD;
SHOW ROW ACCESS POLICIES IN SCHEMA ADVENTURE_WORKS_DB.GOLD;

-- Check which columns have masking policies applied
SELECT
    TABLE_CATALOG,
    TABLE_SCHEMA,
    TABLE_NAME,
    COLUMN_NAME,
    MASKING_POLICY_NAME
FROM TABLE(
    ADVENTURE_WORKS_DB.INFORMATION_SCHEMA.POLICY_REFERENCES(
        POLICY_NAME => 'ADVENTURE_WORKS_DB.GOLD.MASK_EMAIL_ADDRESS'
    )
);
