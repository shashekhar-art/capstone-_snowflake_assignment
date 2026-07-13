-- =============================================================================
-- ROLE-BASED ACCESS CONTROL (RBAC)
-- Capstone Project - Adventure Works Sales Analytics
-- Milestone 7: Security & Governance
--
-- Roles (as specified in assignment):
--   ADMIN_ROLE          -> Full administrative access across all layers
--   DATA_ENGINEER_ROLE  -> ETL access: full on BRONZE/SILVER, write on GOLD
--   ANALYST_ROLE        -> Read-only access on GOLD tables and views
-- =============================================================================

USE ROLE SYSADMIN;
USE WAREHOUSE COMPUTE_WH;

-- =============================================================================
-- 1. CREATE ROLES
-- =============================================================================

-- Role hierarchy:
-- SYSADMIN
--   └─ ADMIN_ROLE
--        ├─ DATA_ENGINEER_ROLE  (full ETL access: BRONZE + SILVER + GOLD write)
--        └─ ANALYST_ROLE        (read-only: GOLD tables and views)

CREATE ROLE IF NOT EXISTS ADMIN_ROLE
    COMMENT = 'Administrative role — full control over all capstone objects';

CREATE ROLE IF NOT EXISTS DATA_ENGINEER_ROLE
    COMMENT = 'ETL pipeline role — full DML on BRONZE and SILVER, write on GOLD';

CREATE ROLE IF NOT EXISTS ANALYST_ROLE
    COMMENT = 'Analytics role — read-only SELECT on GOLD tables and analytical views';

-- Role hierarchy grants
GRANT ROLE DATA_ENGINEER_ROLE TO ROLE ADMIN_ROLE;
GRANT ROLE ANALYST_ROLE        TO ROLE ADMIN_ROLE;

-- Elevate ADMIN_ROLE under SYSADMIN
GRANT ROLE ADMIN_ROLE TO ROLE SYSADMIN;

-- =============================================================================
-- 2. WAREHOUSE GRANTS
-- =============================================================================

-- ADMIN_ROLE and DATA_ENGINEER_ROLE use the main compute warehouse
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE ADMIN_ROLE;
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE DATA_ENGINEER_ROLE;

-- ANALYST_ROLE uses the same warehouse (or a dedicated analytics WH if created)
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE ANALYST_ROLE;

-- =============================================================================
-- 3. DATABASE GRANTS
-- =============================================================================

-- All roles need usage on the database
GRANT USAGE ON DATABASE ADVENTURE_WORKS_DB TO ROLE ADMIN_ROLE;
GRANT USAGE ON DATABASE ADVENTURE_WORKS_DB TO ROLE DATA_ENGINEER_ROLE;
GRANT USAGE ON DATABASE ADVENTURE_WORKS_DB TO ROLE ANALYST_ROLE;

-- =============================================================================
-- 4. SCHEMA GRANTS
-- =============================================================================

-- BRONZE (RAW) schema — Admin + Data Engineer only
GRANT USAGE, CREATE TABLE, CREATE STAGE, CREATE FILE FORMAT
    ON SCHEMA ADVENTURE_WORKS_DB.BRONZE TO ROLE ADMIN_ROLE;

GRANT USAGE, CREATE TABLE, CREATE STAGE
    ON SCHEMA ADVENTURE_WORKS_DB.BRONZE TO ROLE DATA_ENGINEER_ROLE;

-- No BRONZE access for ANALYST_ROLE (raw data is not analyst-facing)

-- SILVER (CURATED) schema — Admin + Data Engineer write; Analyst read
GRANT USAGE, CREATE TABLE
    ON SCHEMA ADVENTURE_WORKS_DB.SILVER TO ROLE ADMIN_ROLE;

GRANT USAGE, CREATE TABLE
    ON SCHEMA ADVENTURE_WORKS_DB.SILVER TO ROLE DATA_ENGINEER_ROLE;

GRANT USAGE
    ON SCHEMA ADVENTURE_WORKS_DB.SILVER TO ROLE ANALYST_ROLE;

-- GOLD (ANALYTICS) schema — Admin + Data Engineer write; Analyst read
GRANT USAGE, CREATE TABLE, CREATE VIEW, CREATE MATERIALIZED VIEW
    ON SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE ADMIN_ROLE;

GRANT USAGE, CREATE TABLE, CREATE VIEW
    ON SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE DATA_ENGINEER_ROLE;

GRANT USAGE
    ON SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE ANALYST_ROLE;

-- =============================================================================
-- 5. TABLE-LEVEL GRANTS
-- =============================================================================

-- BRONZE — Data Engineer full DML
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON ALL TABLES IN SCHEMA ADVENTURE_WORKS_DB.BRONZE TO ROLE DATA_ENGINEER_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON FUTURE TABLES IN SCHEMA ADVENTURE_WORKS_DB.BRONZE TO ROLE DATA_ENGINEER_ROLE;

-- Admin inherits from Data Engineer via role hierarchy
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, DROP
    ON ALL TABLES IN SCHEMA ADVENTURE_WORKS_DB.BRONZE TO ROLE ADMIN_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE, DROP
    ON FUTURE TABLES IN SCHEMA ADVENTURE_WORKS_DB.BRONZE TO ROLE ADMIN_ROLE;

-- SILVER — Data Engineer full DML; Analyst SELECT only
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON ALL TABLES IN SCHEMA ADVENTURE_WORKS_DB.SILVER TO ROLE DATA_ENGINEER_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON FUTURE TABLES IN SCHEMA ADVENTURE_WORKS_DB.SILVER TO ROLE DATA_ENGINEER_ROLE;
GRANT SELECT
    ON ALL TABLES IN SCHEMA ADVENTURE_WORKS_DB.SILVER TO ROLE ANALYST_ROLE;
GRANT SELECT
    ON FUTURE TABLES IN SCHEMA ADVENTURE_WORKS_DB.SILVER TO ROLE ANALYST_ROLE;

-- GOLD — Data Engineer write; Analyst SELECT only
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON ALL TABLES IN SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE DATA_ENGINEER_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE
    ON FUTURE TABLES IN SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE DATA_ENGINEER_ROLE;
GRANT SELECT
    ON ALL TABLES IN SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE ANALYST_ROLE;
GRANT SELECT
    ON FUTURE TABLES IN SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE ANALYST_ROLE;

-- =============================================================================
-- 6. VIEW GRANTS — GOLD analytical views
-- =============================================================================

GRANT SELECT
    ON ALL VIEWS IN SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE ANALYST_ROLE;
GRANT SELECT
    ON FUTURE VIEWS IN SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE ANALYST_ROLE;

GRANT SELECT
    ON ALL VIEWS IN SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE ADMIN_ROLE;
GRANT SELECT
    ON FUTURE VIEWS IN SCHEMA ADVENTURE_WORKS_DB.GOLD TO ROLE ADMIN_ROLE;

-- =============================================================================
-- 7. CREATE SAMPLE USERS AND ASSIGN ROLES
-- =============================================================================

CREATE USER IF NOT EXISTS ETL_SERVICE_USER
    PASSWORD             = 'Change_Me_2024!'
    DEFAULT_ROLE         = DATA_ENGINEER_ROLE
    DEFAULT_WAREHOUSE    = COMPUTE_WH
    DEFAULT_NAMESPACE    = ADVENTURE_WORKS_DB.BRONZE
    MUST_CHANGE_PASSWORD = TRUE
    COMMENT              = 'Service account for ETL pipeline execution';

CREATE USER IF NOT EXISTS ANALYST_USER
    PASSWORD             = 'Change_Me_2024!'
    DEFAULT_ROLE         = ANALYST_ROLE
    DEFAULT_WAREHOUSE    = COMPUTE_WH
    DEFAULT_NAMESPACE    = ADVENTURE_WORKS_DB.GOLD
    MUST_CHANGE_PASSWORD = TRUE
    COMMENT              = 'Analytics user — read-only on GOLD layer';

GRANT ROLE DATA_ENGINEER_ROLE TO USER ETL_SERVICE_USER;
GRANT ROLE ANALYST_ROLE        TO USER ANALYST_USER;

-- =============================================================================
-- 8. VERIFY GRANTS
-- =============================================================================

SHOW ROLES;
SHOW GRANTS TO ROLE ADMIN_ROLE;
SHOW GRANTS TO ROLE DATA_ENGINEER_ROLE;
SHOW GRANTS TO ROLE ANALYST_ROLE;
SHOW GRANTS ON DATABASE ADVENTURE_WORKS_DB;
SHOW GRANTS ON SCHEMA ADVENTURE_WORKS_DB.GOLD;
