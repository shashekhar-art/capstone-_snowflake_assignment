-- BRONZE LAYER DDL
-- Adventure Works Capstone Project
-- Purpose : Create raw ingestion tables in the BRONZE schema.
--           No transformations — all columns stored as VARCHAR or NUMBER
--           matching the source CSV exactly.

-- ── Database & Schema ─────────────────────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS ADVENTURE_WORKS_DB;
CREATE SCHEMA  IF NOT EXISTS ADVENTURE_WORKS_DB.BRONZE;

-- ── Warehouse ─────────────────────────────────────────────────────────────────
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND   = 60
    AUTO_RESUME    = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Capstone project shared warehouse';

-- ── File Format ───────────────────────────────────────────────────────────────
CREATE OR REPLACE FILE FORMAT ADVENTURE_WORKS_DB.BRONZE.CSV_FORMAT
    TYPE                        = 'CSV'
    FIELD_DELIMITER             = ','
    RECORD_DELIMITER            = '\n'
    SKIP_HEADER                 = 1
    NULL_IF                     = ('NULL', 'null', 'N/A', '')
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    EMPTY_FIELD_AS_NULL         = TRUE
    TRIM_SPACE                  = TRUE
    DATE_FORMAT                 = 'AUTO'
    COMMENT                     = 'Standard CSV format for Adventure Works source files';

-- ── Internal Stage ────────────────────────────────────────────────────────────
CREATE STAGE IF NOT EXISTS ADVENTURE_WORKS_DB.BRONZE.RAW_DATA_STAGE
    FILE_FORMAT = ADVENTURE_WORKS_DB.BRONZE.CSV_FORMAT
    COMMENT     = 'Internal stage for raw CSV uploads';

-- BRONZE TABLES

-- Sales 2020
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_SALES_2020 (
    ORDERDATE       VARCHAR(20)     COMMENT 'Order date as raw string',
    STOCKDATE       VARCHAR(20)     COMMENT 'Stock date as raw string',
    ORDERNUMBER     VARCHAR(20)     COMMENT 'Order identifier',
    PRODUCTKEY      NUMBER          COMMENT 'FK to product',
    CUSTOMERKEY     NUMBER          COMMENT 'FK to customer',
    TERRITORYKEY    NUMBER          COMMENT 'FK to territory',
    ORDERLINEITEM   NUMBER          COMMENT 'Line item number within order',
    ORDERQUANTITY   NUMBER          COMMENT 'Quantity ordered',
    LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() COMMENT 'ETL load time',
    SOURCE_FILE     VARCHAR(100)  DEFAULT 'Sales Data 2020.csv'
)
COMMENT = 'Raw sales transactions for calendar year 2020';

-- Sales 2021
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_SALES_2021 (
    ORDERDATE       VARCHAR(20),
    STOCKDATE       VARCHAR(20),
    ORDERNUMBER     VARCHAR(20),
    PRODUCTKEY      NUMBER,
    CUSTOMERKEY     NUMBER,
    TERRITORYKEY    NUMBER,
    ORDERLINEITEM   NUMBER,
    ORDERQUANTITY   NUMBER,
    LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE     VARCHAR(100)  DEFAULT 'Sales Data 2021.csv'
)
COMMENT = 'Raw sales transactions for calendar year 2021';

-- Sales 2022
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_SALES_2022 (
    ORDERDATE       VARCHAR(20),
    STOCKDATE       VARCHAR(20),
    ORDERNUMBER     VARCHAR(20),
    PRODUCTKEY      NUMBER,
    CUSTOMERKEY     NUMBER,
    TERRITORYKEY    NUMBER,
    ORDERLINEITEM   NUMBER,
    ORDERQUANTITY   NUMBER,
    LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE     VARCHAR(100)  DEFAULT 'Sales Data 2022.csv'
)
COMMENT = 'Raw sales transactions for calendar year 2022';

-- Customer Lookup
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_CUSTOMER (
    CUSTOMERKEY     NUMBER          COMMENT 'Customer natural key',
    PREFIX          VARCHAR(10),
    FIRSTNAME       VARCHAR(50),
    LASTNAME        VARCHAR(50),
    BIRTHDATE       VARCHAR(20)     COMMENT 'Raw date string',
    MARITALSTATUS   VARCHAR(5)      COMMENT 'M=Married, S=Single',
    GENDER          VARCHAR(5)      COMMENT 'M=Male, F=Female',
    EMAILADDRESS    VARCHAR(100),
    ANNUALINCOME    NUMBER,
    TOTALCHILDREN   NUMBER,
    EDUCATIONLEVEL  VARCHAR(50),
    OCCUPATION      VARCHAR(50),
    HOMEOWNER       VARCHAR(5)      COMMENT 'Y/N flag',
    LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE     VARCHAR(100)  DEFAULT 'Customer Lookup.csv'
)
COMMENT = 'Raw customer master data';

-- Product Lookup
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_PRODUCT (
    PRODUCTKEY              NUMBER,
    PRODUCTSUBCATEGORYKEY   NUMBER,
    PRODUCTSKU              VARCHAR(20),
    PRODUCTNAME             VARCHAR(200),
    MODELNAME               VARCHAR(100),
    PRODUCTDESCRIPTION      VARCHAR(500),
    PRODUCTCOLOR            VARCHAR(30),
    PRODUCTSIZE             VARCHAR(10),
    PRODUCTSTYLE            VARCHAR(10),
    PRODUCTCOST             NUMBER(12,4),
    PRODUCTPRICE            NUMBER(12,4),
    LOAD_TIMESTAMP          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE             VARCHAR(100)  DEFAULT 'Product Lookup.csv'
)
COMMENT = 'Raw product catalogue';

-- Product Categories
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_PRODUCT_CATEGORY (
    PRODUCTCATEGORYKEY  NUMBER,
    CATEGORYNAME        VARCHAR(50),
    LOAD_TIMESTAMP      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE         VARCHAR(100)  DEFAULT 'Product Categories Lookup.csv'
)
COMMENT = 'Product top-level categories (Bikes, Components, Clothing, Accessories)';

-- Subcategories
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_SUBCATEGORY (
    PRODUCTSUBCATEGORYKEY   NUMBER,
    SUBCATEGORYNAME         VARCHAR(100),
    PRODUCTCATEGORYKEY      NUMBER,
    LOAD_TIMESTAMP          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE             VARCHAR(100)  DEFAULT 'Subcategories Lookup.csv'
)
COMMENT = 'Product sub-categories linked to categories';

-- Calendar Lookup
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_CALENDAR (
    DATE            VARCHAR(20)     COMMENT 'Date as raw string (YYYY-MM-DD)',
    LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE     VARCHAR(100)  DEFAULT 'Calendar Lookup.csv'
)
COMMENT = 'Raw calendar spine covering 2020–2022';

-- Territory Lookup
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_TERRITORY (
    SALESTERRITORYKEY   NUMBER,
    REGION              VARCHAR(50),
    COUNTRY             VARCHAR(50),
    CONTINENT           VARCHAR(50),
    LOAD_TIMESTAMP      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE         VARCHAR(100)  DEFAULT 'Territory Lookup.csv'
)
COMMENT = 'Sales territory geographical reference';

-- Returns Data
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_RETURNS (
    RETURNDATE      VARCHAR(20),
    TERRITORYKEY    NUMBER,
    PRODUCTKEY      NUMBER,
    RETURNQUANTITY  NUMBER,
    LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE     VARCHAR(100)  DEFAULT 'Returns Data.csv'
)
COMMENT = 'Raw product return transactions';

-- Product Category Sales (Unpivot source)
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_CATEGORY_SALES_UNPIVOT (
    DATE                VARCHAR(20),
    PRODUCT_CATEGORY    VARCHAR(50),
    NORTH_REGION        NUMBER,
    CENTRAL_REGION      NUMBER,
    SOUTH_REGION        NUMBER,
    LOAD_TIMESTAMP      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    SOURCE_FILE         VARCHAR(100)  DEFAULT 'Product Category Sales (Unpivot Demo).csv'
)
COMMENT = 'Pivoted category sales by region — used for UNPIVOT demonstration';

-- VERIFICATION QUERIES
-- SELECT TABLE_SCHEMA, TABLE_NAME, ROW_COUNT, BYTES
-- FROM   ADVENTURE_WORKS_DB.INFORMATION_SCHEMA.TABLES
-- WHERE  TABLE_SCHEMA = 'BRONZE'
-- ORDER BY TABLE_NAME;
