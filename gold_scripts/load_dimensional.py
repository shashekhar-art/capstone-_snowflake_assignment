"""
Gold Layer - Load Dimension Tables (Star Schema)
Builds conformed dimensions for the Adventure Works sales data mart.

Dimensions created:
  DIM_DATE      - Enriched calendar with fiscal attributes
  DIM_CUSTOMER  - SCD Type 1 customer master
  DIM_PRODUCT   - Product with category hierarchy
  DIM_TERRITORY - Geography hierarchy
"""
import sys
import os
import logging
from datetime import datetime

import snowflake.connector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.snowflake_config import SNOWFLAKE_CONFIG, SILVER_SCHEMA, GOLD_SCHEMA

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def get_connection():
    cfg = dict(SNOWFLAKE_CONFIG)
    cfg["schema"] = GOLD_SCHEMA
    return snowflake.connector.connect(**cfg)


# ── Gold Schema Bootstrap ──────────────────────────────────────────────────────

GOLD_SCHEMA_SQL = f"CREATE SCHEMA IF NOT EXISTS ADVENTURE_WORKS_DB.{GOLD_SCHEMA};"


# ── Dimension DDL + Populate ───────────────────────────────────────────────────

DIM_DATE = """
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.GOLD.DIM_DATE AS
SELECT
    DATE_KEY,
    YEAR                            AS YEAR,
    MONTH_NUM,
    MONTH_NAME,
    DAY_OF_MONTH,
    DAY_OF_WEEK_NAME,
    DAY_OF_WEEK_NUM,
    QUARTER_NUM,
    QUARTER_NAME,
    WEEK_OF_YEAR,
    IS_WEEKEND,
    FIRST_DAY_OF_MONTH,
    LAST_DAY_OF_MONTH,
    -- Fiscal year (assume fiscal year starts July 1)
    CASE WHEN MONTH_NUM >= 7
         THEN YEAR + 1 ELSE YEAR
    END                              AS FISCAL_YEAR,
    CASE WHEN MONTH_NUM >= 7
         THEN MONTH_NUM - 6
         ELSE MONTH_NUM + 6
    END                              AS FISCAL_MONTH,
    CASE
        WHEN MONTH_NUM IN (7,8,9)   THEN 'FQ1'
        WHEN MONTH_NUM IN (10,11,12) THEN 'FQ2'
        WHEN MONTH_NUM IN (1,2,3)   THEN 'FQ3'
        ELSE                             'FQ4'
    END                              AS FISCAL_QUARTER,
    CURRENT_TIMESTAMP()              AS LOAD_TIMESTAMP
FROM ADVENTURE_WORKS_DB.SILVER.SILVER_CALENDAR
WHERE DATE_KEY IS NOT NULL;
"""

DIM_CUSTOMER = """
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER AS
SELECT
    CUSTOMER_KEY,
    PREFIX,
    FIRST_NAME,
    LAST_NAME,
    FULL_NAME,
    BIRTH_DATE,
    AGE,
    MARITAL_STATUS,
    GENDER,
    EMAIL_ADDRESS,
    ANNUAL_INCOME,
    INCOME_BAND,
    TOTAL_CHILDREN,
    EDUCATION_LEVEL,
    OCCUPATION,
    IS_HOME_OWNER,
    CURRENT_TIMESTAMP() AS LOAD_TIMESTAMP
FROM ADVENTURE_WORKS_DB.SILVER.SILVER_CUSTOMER;
"""

DIM_PRODUCT = """
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT AS
SELECT
    PRODUCT_KEY,
    PRODUCT_SKU,
    PRODUCT_NAME,
    MODEL_NAME,
    PRODUCT_DESCRIPTION,
    PRODUCT_COLOR,
    PRODUCT_SIZE,
    PRODUCT_STYLE,
    PRODUCT_COST,
    PRODUCT_PRICE,
    GROSS_MARGIN,
    MARGIN_PCT,
    SUBCATEGORY_KEY,
    SUBCATEGORY_NAME,
    CATEGORY_KEY,
    CATEGORY_NAME,
    -- Price tier segmentation
    CASE
        WHEN PRODUCT_PRICE < 50    THEN 'Budget'
        WHEN PRODUCT_PRICE < 250   THEN 'Mid-Range'
        WHEN PRODUCT_PRICE < 1000  THEN 'Premium'
        ELSE                            'Luxury'
    END                      AS PRICE_TIER,
    CURRENT_TIMESTAMP()      AS LOAD_TIMESTAMP
FROM ADVENTURE_WORKS_DB.SILVER.SILVER_PRODUCT;
"""

DIM_TERRITORY = """
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.GOLD.DIM_TERRITORY AS
SELECT
    TERRITORY_KEY,
    REGION,
    COUNTRY,
    CONTINENT,
    -- Abbreviated region codes
    CASE REGION
        WHEN 'Northwest'    THEN 'NW'
        WHEN 'Northeast'    THEN 'NE'
        WHEN 'Central'      THEN 'CTR'
        WHEN 'Southwest'    THEN 'SW'
        WHEN 'Southeast'    THEN 'SE'
        WHEN 'Canada'       THEN 'CAN'
        WHEN 'France'       THEN 'FR'
        WHEN 'Germany'      THEN 'DE'
        WHEN 'Australia'    THEN 'AU'
        WHEN 'United Kingdom' THEN 'UK'
        ELSE UPPER(LEFT(REGION, 3))
    END                      AS REGION_CODE,
    CURRENT_TIMESTAMP()      AS LOAD_TIMESTAMP
FROM ADVENTURE_WORKS_DB.SILVER.SILVER_TERRITORY;
"""

DIMENSIONS = {
    "DIM_DATE":      DIM_DATE,
    "DIM_CUSTOMER":  DIM_CUSTOMER,
    "DIM_PRODUCT":   DIM_PRODUCT,
    "DIM_TERRITORY": DIM_TERRITORY,
}


# ── Primary Key Constraints (informational) ────────────────────────────────────

PK_SQL = {
    "DIM_DATE":      "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_DATE      ADD PRIMARY KEY (DATE_KEY)     RELY NOVALIDATE;",
    "DIM_CUSTOMER":  "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER  ADD PRIMARY KEY (CUSTOMER_KEY) RELY NOVALIDATE;",
    "DIM_PRODUCT":   "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT   ADD PRIMARY KEY (PRODUCT_KEY)  RELY NOVALIDATE;",
    "DIM_TERRITORY": "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.DIM_TERRITORY ADD PRIMARY KEY (TERRITORY_KEY) RELY NOVALIDATE;",
}


def main():
    log.info("=== GOLD LAYER - DIMENSION LOAD STARTED ===")
    conn = get_connection()
    cur = conn.cursor()

    log.info("Creating GOLD schema ...")
    cur.execute(GOLD_SCHEMA_SQL)

    for dim_name, sql in DIMENSIONS.items():
        log.info("Building %s ...", dim_name)
        start = datetime.now()
        try:
            cur.execute(sql)
            cur.execute(f"SELECT COUNT(*) FROM ADVENTURE_WORKS_DB.GOLD.{dim_name}")
            rows = cur.fetchone()[0]
            elapsed = (datetime.now() - start).total_seconds()
            log.info("  %-20s -> %8s rows  (%.1fs)", dim_name, f"{rows:,}", elapsed)

            cur.execute(PK_SQL[dim_name])
            log.info("  Primary key set on %s", dim_name)
        except Exception as exc:
            log.error("  FAILED %s: %s", dim_name, exc)

    cur.close()
    conn.close()
    log.info("=== DIMENSION LOAD COMPLETE ===")


if __name__ == "__main__":
    main()
