"""
Silver Layer - Data Transformation Script
Cleanses, enriches, and standardises Bronze data into the SILVER schema.
Transformations applied:
  - Type casting (VARCHAR → DATE, NUMBER, etc.)
  - NULL handling and default substitution
  - Name standardisation (INITCAP)
  - Derived columns (age, full_name, profit_margin, etc.)
  - Consolidation: BRONZE_SALES_2020/21/22 → SILVER_SALES (with SALES_YEAR)
  - Calendar enrichment: day_of_week, month_name, quarter, is_weekend
"""
import sys
import os
import logging
from datetime import datetime

import snowflake.connector

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.snowflake_config import SNOWFLAKE_CONFIG, BRONZE_SCHEMA, SILVER_SCHEMA

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ── Connection ─────────────────────────────────────────────────────────────────

def get_connection():
    cfg = dict(SNOWFLAKE_CONFIG)
    cfg["schema"] = SILVER_SCHEMA
    return snowflake.connector.connect(**cfg)


# ── Silver DDL + Transform SQL ─────────────────────────────────────────────────

SILVER_TRANSFORMS = {

    "SILVER_CALENDAR": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_CALENDAR AS
        SELECT
            TRY_TO_DATE(DATE, 'YYYY-MM-DD')           AS DATE_KEY,
            DATE_PART('year',  TRY_TO_DATE(DATE))     AS YEAR,
            DATE_PART('month', TRY_TO_DATE(DATE))     AS MONTH_NUM,
            MONTHNAME(TRY_TO_DATE(DATE))               AS MONTH_NAME,
            DATE_PART('day',   TRY_TO_DATE(DATE))     AS DAY_OF_MONTH,
            DAYNAME(TRY_TO_DATE(DATE))                 AS DAY_OF_WEEK_NAME,
            DATE_PART('dayofweek', TRY_TO_DATE(DATE)) AS DAY_OF_WEEK_NUM,
            DATE_PART('quarter', TRY_TO_DATE(DATE))   AS QUARTER_NUM,
            'Q' || DATE_PART('quarter', TRY_TO_DATE(DATE)) AS QUARTER_NAME,
            DATE_PART('week', TRY_TO_DATE(DATE))      AS WEEK_OF_YEAR,
            IFF(DAYNAME(TRY_TO_DATE(DATE)) IN ('Sat','Sun'), TRUE, FALSE) AS IS_WEEKEND,
            DATE_TRUNC('month', TRY_TO_DATE(DATE))    AS FIRST_DAY_OF_MONTH,
            LAST_DAY(TRY_TO_DATE(DATE))                AS LAST_DAY_OF_MONTH,
            CURRENT_TIMESTAMP()                        AS LOAD_TIMESTAMP
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_CALENDAR
        WHERE TRY_TO_DATE(DATE, 'YYYY-MM-DD') IS NOT NULL;
    """,

    "SILVER_TERRITORY": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_TERRITORY AS
        SELECT
            SALESTERRITORYKEY                          AS TERRITORY_KEY,
            TRIM(INITCAP(REGION))                      AS REGION,
            TRIM(INITCAP(COUNTRY))                     AS COUNTRY,
            TRIM(INITCAP(CONTINENT))                   AS CONTINENT,
            CURRENT_TIMESTAMP()                        AS LOAD_TIMESTAMP
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_TERRITORY
        WHERE SALESTERRITORYKEY IS NOT NULL;
    """,

    "SILVER_PRODUCT_CATEGORY": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_PRODUCT_CATEGORY AS
        SELECT
            pc.PRODUCTCATEGORYKEY                      AS CATEGORY_KEY,
            TRIM(pc.CATEGORYNAME)                      AS CATEGORY_NAME,
            sc.PRODUCTSUBCATEGORYKEY                   AS SUBCATEGORY_KEY,
            TRIM(sc.SUBCATEGORYNAME)                   AS SUBCATEGORY_NAME,
            CURRENT_TIMESTAMP()                        AS LOAD_TIMESTAMP
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_PRODUCT_CATEGORY pc
        LEFT JOIN ADVENTURE_WORKS_DB.BRONZE.BRONZE_SUBCATEGORY sc
               ON pc.PRODUCTCATEGORYKEY = sc.PRODUCTCATEGORYKEY;
    """,

    "SILVER_PRODUCT": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_PRODUCT AS
        SELECT
            p.PRODUCTKEY                               AS PRODUCT_KEY,
            p.PRODUCTSUBCATEGORYKEY                    AS SUBCATEGORY_KEY,
            TRIM(p.PRODUCTSKU)                         AS PRODUCT_SKU,
            TRIM(p.PRODUCTNAME)                        AS PRODUCT_NAME,
            TRIM(p.MODELNAME)                          AS MODEL_NAME,
            TRIM(p.PRODUCTDESCRIPTION)                 AS PRODUCT_DESCRIPTION,
            COALESCE(TRIM(NULLIF(p.PRODUCTCOLOR,'0')), 'Unknown') AS PRODUCT_COLOR,
            COALESCE(TRIM(NULLIF(p.PRODUCTSIZE, '0')), 'N/A')     AS PRODUCT_SIZE,
            COALESCE(TRIM(NULLIF(p.PRODUCTSTYLE,'0')), 'N/A')     AS PRODUCT_STYLE,
            ROUND(p.PRODUCTCOST::FLOAT,  4)            AS PRODUCT_COST,
            ROUND(p.PRODUCTPRICE::FLOAT, 4)            AS PRODUCT_PRICE,
            ROUND(p.PRODUCTPRICE::FLOAT - p.PRODUCTCOST::FLOAT, 4) AS GROSS_MARGIN,
            ROUND((p.PRODUCTPRICE::FLOAT - p.PRODUCTCOST::FLOAT)
                   / NULLIF(p.PRODUCTPRICE::FLOAT, 0) * 100, 2)   AS MARGIN_PCT,
            sc.SUBCATEGORYNAME                         AS SUBCATEGORY_NAME,
            cat.CATEGORYNAME                           AS CATEGORY_NAME,
            cat.PRODUCTCATEGORYKEY                     AS CATEGORY_KEY,
            CURRENT_TIMESTAMP()                        AS LOAD_TIMESTAMP
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_PRODUCT p
        LEFT JOIN ADVENTURE_WORKS_DB.BRONZE.BRONZE_SUBCATEGORY sc
               ON p.PRODUCTSUBCATEGORYKEY = sc.PRODUCTSUBCATEGORYKEY
        LEFT JOIN ADVENTURE_WORKS_DB.BRONZE.BRONZE_PRODUCT_CATEGORY cat
               ON sc.PRODUCTCATEGORYKEY = cat.PRODUCTCATEGORYKEY
        WHERE p.PRODUCTKEY IS NOT NULL;
    """,

    "SILVER_CUSTOMER": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_CUSTOMER AS
        SELECT
            CUSTOMERKEY                                AS CUSTOMER_KEY,
            TRIM(PREFIX)                               AS PREFIX,
            INITCAP(TRIM(FIRSTNAME))                   AS FIRST_NAME,
            INITCAP(TRIM(LASTNAME))                    AS LAST_NAME,
            INITCAP(TRIM(FIRSTNAME)) || ' '
              || INITCAP(TRIM(LASTNAME))               AS FULL_NAME,
            TRY_TO_DATE(BIRTHDATE, 'YYYY-MM-DD')       AS BIRTH_DATE,
            DATEDIFF('year',
                TRY_TO_DATE(BIRTHDATE, 'YYYY-MM-DD'),
                CURRENT_DATE())                        AS AGE,
            CASE MARITALSTATUS
                WHEN 'M' THEN 'Married'
                WHEN 'S' THEN 'Single'
                ELSE 'Unknown' END                     AS MARITAL_STATUS,
            CASE GENDER
                WHEN 'M' THEN 'Male'
                WHEN 'F' THEN 'Female'
                ELSE 'Unknown' END                     AS GENDER,
            LOWER(TRIM(EMAILADDRESS))                  AS EMAIL_ADDRESS,
            COALESCE(ANNUALINCOME, 0)                  AS ANNUAL_INCOME,
            CASE
                WHEN ANNUALINCOME < 40000  THEN 'Low'
                WHEN ANNUALINCOME < 80000  THEN 'Medium'
                WHEN ANNUALINCOME < 120000 THEN 'High'
                ELSE 'Very High' END                   AS INCOME_BAND,
            COALESCE(TOTALCHILDREN, 0)                 AS TOTAL_CHILDREN,
            COALESCE(TRIM(EDUCATIONLEVEL), 'Unknown')  AS EDUCATION_LEVEL,
            COALESCE(TRIM(OCCUPATION),     'Unknown')  AS OCCUPATION,
            CASE HOMEOWNER WHEN 'Y' THEN TRUE ELSE FALSE END AS IS_HOME_OWNER,
            CURRENT_TIMESTAMP()                        AS LOAD_TIMESTAMP
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_CUSTOMER
        WHERE CUSTOMERKEY IS NOT NULL;
    """,

    "SILVER_SALES": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_SALES AS
        SELECT
            ORDERNUMBER                                AS ORDER_NUMBER,
            ORDERLINEITEM                              AS ORDER_LINE_ITEM,
            TRY_TO_DATE(ORDERDATE, 'YYYY-MM-DD')       AS ORDER_DATE,
            TRY_TO_DATE(STOCKDATE, 'YYYY-MM-DD')       AS STOCK_DATE,
            DATEDIFF('day',
                TRY_TO_DATE(STOCKDATE),
                TRY_TO_DATE(ORDERDATE))                AS DAYS_FROM_STOCK_TO_ORDER,
            PRODUCTKEY                                 AS PRODUCT_KEY,
            CUSTOMERKEY                                AS CUSTOMER_KEY,
            TERRITORYKEY                               AS TERRITORY_KEY,
            COALESCE(ORDERQUANTITY, 0)                 AS ORDER_QUANTITY,
            2020                                       AS SALES_YEAR,
            SOURCE_FILE
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_SALES_2020
        WHERE ORDERNUMBER IS NOT NULL

        UNION ALL

        SELECT
            ORDERNUMBER, ORDERLINEITEM,
            TRY_TO_DATE(ORDERDATE, 'YYYY-MM-DD'),
            TRY_TO_DATE(STOCKDATE, 'YYYY-MM-DD'),
            DATEDIFF('day',
                TRY_TO_DATE(STOCKDATE),
                TRY_TO_DATE(ORDERDATE)),
            PRODUCTKEY, CUSTOMERKEY, TERRITORYKEY,
            COALESCE(ORDERQUANTITY, 0),
            2021, SOURCE_FILE
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_SALES_2021
        WHERE ORDERNUMBER IS NOT NULL

        UNION ALL

        SELECT
            ORDERNUMBER, ORDERLINEITEM,
            TRY_TO_DATE(ORDERDATE, 'YYYY-MM-DD'),
            TRY_TO_DATE(STOCKDATE, 'YYYY-MM-DD'),
            DATEDIFF('day',
                TRY_TO_DATE(STOCKDATE),
                TRY_TO_DATE(ORDERDATE)),
            PRODUCTKEY, CUSTOMERKEY, TERRITORYKEY,
            COALESCE(ORDERQUANTITY, 0),
            2022, SOURCE_FILE
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_SALES_2022
        WHERE ORDERNUMBER IS NOT NULL;
    """,

    "SILVER_RETURNS": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_RETURNS AS
        SELECT
            TRY_TO_DATE(RETURNDATE, 'YYYY-MM-DD')      AS RETURN_DATE,
            TERRITORYKEY                               AS TERRITORY_KEY,
            PRODUCTKEY                                 AS PRODUCT_KEY,
            COALESCE(RETURNQUANTITY, 0)                AS RETURN_QUANTITY,
            CURRENT_TIMESTAMP()                        AS LOAD_TIMESTAMP
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_RETURNS
        WHERE RETURNDATE IS NOT NULL;
    """,

    "SILVER_CATEGORY_SALES_UNPIVOT": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_CATEGORY_SALES_UNPIVOT AS
        SELECT
            TRY_TO_DATE(DATE, 'M/D/YYYY')              AS SALE_DATE,
            TRIM(PRODUCT_CATEGORY)                     AS PRODUCT_CATEGORY,
            'North'   AS REGION,
            COALESCE(NORTH_REGION,   0)                AS SALES_AMOUNT
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_CATEGORY_SALES_UNPIVOT

        UNION ALL SELECT
            TRY_TO_DATE(DATE, 'M/D/YYYY'),
            TRIM(PRODUCT_CATEGORY), 'Central',
            COALESCE(CENTRAL_REGION, 0)
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_CATEGORY_SALES_UNPIVOT

        UNION ALL SELECT
            TRY_TO_DATE(DATE, 'M/D/YYYY'),
            TRIM(PRODUCT_CATEGORY), 'South',
            COALESCE(SOUTH_REGION,   0)
        FROM ADVENTURE_WORKS_DB.BRONZE.BRONZE_CATEGORY_SALES_UNPIVOT;
    """,
}

SILVER_SCHEMA_SQL = f"CREATE SCHEMA IF NOT EXISTS ADVENTURE_WORKS_DB.{SILVER_SCHEMA};"


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_transform(conn, name: str, sql: str):
    cur = conn.cursor()
    start = datetime.now()
    try:
        cur.execute(sql)
        elapsed = (datetime.now() - start).total_seconds()
        cur.execute(f"SELECT COUNT(*) FROM ADVENTURE_WORKS_DB.{SILVER_SCHEMA}.{name}")
        rows = cur.fetchone()[0]
        log.info("  %-45s -> %8s rows  (%.1fs)", name, f"{rows:,}", elapsed)
        return rows
    except Exception as exc:
        log.error("  FAILED %s: %s", name, exc)
        return 0
    finally:
        cur.close()


def main():
    log.info("=== SILVER LAYER TRANSFORM STARTED ===")
    conn = get_connection()
    cur = conn.cursor()

    log.info("Creating SILVER schema ...")
    cur.execute(SILVER_SCHEMA_SQL)
    cur.close()

    total = 0
    for table_name, sql in SILVER_TRANSFORMS.items():
        log.info("Transforming %s ...", table_name)
        total += run_transform(conn, table_name, sql)

    conn.close()
    log.info("=== SILVER TRANSFORM COMPLETE: %s total rows ===", f"{total:,}")


if __name__ == "__main__":
    main()
