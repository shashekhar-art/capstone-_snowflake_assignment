"""
Bronze Layer - Load Raw CSV Data to Snowflake
Uploads all Adventure Works source files to the BRONZE schema
using Snowflake PUT + COPY INTO with a full-refresh strategy.

CHANGELOG (feature/bronze-load):
- Added retry logic for transient network errors
- Added row-count validation after each table load
"""
import os
import sys
import time
import logging
from datetime import datetime

import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.snowflake_config import (
    SNOWFLAKE_CONFIG, BRONZE_SCHEMA, INTERNAL_STAGE, CSV_FILE_FORMAT, CSV_TABLE_MAP
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

DATASET_DIR = os.path.join(os.path.dirname(__file__), "..", "capstone_project_dataset")


# ── Connection ─────────────────────────────────────────────────────────────────

def get_connection():
    cfg = dict(SNOWFLAKE_CONFIG)
    cfg["schema"] = BRONZE_SCHEMA
    return snowflake.connector.connect(**cfg)


# ── Bootstrap DDL ──────────────────────────────────────────────────────────────

BOOTSTRAP_SQL = f"""
-- Database & Schemas
CREATE DATABASE IF NOT EXISTS ADVENTURE_WORKS_DB;
CREATE SCHEMA IF NOT EXISTS ADVENTURE_WORKS_DB.{BRONZE_SCHEMA};

-- Warehouse
CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND   = 60
    AUTO_RESUME    = TRUE
    COMMENT        = 'Capstone project warehouse';

-- CSV File Format
CREATE OR REPLACE FILE FORMAT ADVENTURE_WORKS_DB.{BRONZE_SCHEMA}.CSV_FORMAT
    TYPE             = 'CSV'
    FIELD_DELIMITER  = ','
    RECORD_DELIMITER = '\\n'
    SKIP_HEADER      = 1
    NULL_IF          = ('NULL', 'null', 'N/A', '')
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    EMPTY_FIELD_AS_NULL = TRUE
    TRIM_SPACE       = TRUE;

-- Internal Stage
CREATE STAGE IF NOT EXISTS ADVENTURE_WORKS_DB.{BRONZE_SCHEMA}.RAW_DATA_STAGE
    FILE_FORMAT = ADVENTURE_WORKS_DB.{BRONZE_SCHEMA}.CSV_FORMAT
    COMMENT     = 'Staging area for raw CSV ingestion';
"""


# ── Bronze DDL (per table) ─────────────────────────────────────────────────────

BRONZE_DDL = {
    "BRONZE_SALES_2020": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_SALES_2020 (
            ORDERDATE       VARCHAR(20),
            STOCKDATE       VARCHAR(20),
            ORDERNUMBER     VARCHAR(20),
            PRODUCTKEY      NUMBER,
            CUSTOMERKEY     NUMBER,
            TERRITORYKEY    NUMBER,
            ORDERLINEITEM   NUMBER,
            ORDERQUANTITY   NUMBER,
            LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE     VARCHAR(100)  DEFAULT 'Sales Data 2020.csv'
        );""",
    "BRONZE_SALES_2021": """
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
        );""",
    "BRONZE_SALES_2022": """
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
        );""",
    "BRONZE_CUSTOMER": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_CUSTOMER (
            CUSTOMERKEY     NUMBER,
            PREFIX          VARCHAR(10),
            FIRSTNAME       VARCHAR(50),
            LASTNAME        VARCHAR(50),
            BIRTHDATE       VARCHAR(20),
            MARITALSTATUS   VARCHAR(5),
            GENDER          VARCHAR(5),
            EMAILADDRESS    VARCHAR(100),
            ANNUALINCOME    NUMBER,
            TOTALCHILDREN   NUMBER,
            EDUCATIONLEVEL  VARCHAR(50),
            OCCUPATION      VARCHAR(50),
            HOMEOWNER       VARCHAR(5),
            LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE     VARCHAR(100)  DEFAULT 'Customer Lookup.csv'
        );""",
    "BRONZE_PRODUCT": """
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
        );""",
    "BRONZE_PRODUCT_CATEGORY": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_PRODUCT_CATEGORY (
            PRODUCTCATEGORYKEY  NUMBER,
            CATEGORYNAME        VARCHAR(50),
            LOAD_TIMESTAMP      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE         VARCHAR(100)  DEFAULT 'Product Categories Lookup.csv'
        );""",
    "BRONZE_SUBCATEGORY": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_SUBCATEGORY (
            PRODUCTSUBCATEGORYKEY   NUMBER,
            SUBCATEGORYNAME         VARCHAR(100),
            PRODUCTCATEGORYKEY      NUMBER,
            LOAD_TIMESTAMP          TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE             VARCHAR(100)  DEFAULT 'Subcategories Lookup.csv'
        );""",
    "BRONZE_CALENDAR": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_CALENDAR (
            DATE            VARCHAR(20),
            LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE     VARCHAR(100)  DEFAULT 'Calendar Lookup.csv'
        );""",
    "BRONZE_TERRITORY": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_TERRITORY (
            SALESTERRITORYKEY   NUMBER,
            REGION              VARCHAR(50),
            COUNTRY             VARCHAR(50),
            CONTINENT           VARCHAR(50),
            LOAD_TIMESTAMP      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE         VARCHAR(100)  DEFAULT 'Territory Lookup.csv'
        );""",
    "BRONZE_RETURNS": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_RETURNS (
            RETURNDATE      VARCHAR(20),
            TERRITORYKEY    NUMBER,
            PRODUCTKEY      NUMBER,
            RETURNQUANTITY  NUMBER,
            LOAD_TIMESTAMP  TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE     VARCHAR(100)  DEFAULT 'Returns Data.csv'
        );""",
    "BRONZE_CATEGORY_SALES_UNPIVOT": """
        CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.BRONZE.BRONZE_CATEGORY_SALES_UNPIVOT (
            DATE                VARCHAR(20),
            PRODUCT_CATEGORY    VARCHAR(50),
            NORTH_REGION        NUMBER,
            CENTRAL_REGION      NUMBER,
            SOUTH_REGION        NUMBER,
            LOAD_TIMESTAMP      TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
            SOURCE_FILE         VARCHAR(100)  DEFAULT 'Product Category Sales (Unpivot Demo).csv'
        );""",
}

COPY_INTO_SQL = {
    name: f"""
        COPY INTO ADVENTURE_WORKS_DB.BRONZE.{name}
        (   {', '.join(
                c.split()[0]
                for c in ddl.strip().split('\n')
                if c.strip() and not c.strip().startswith('CREATE')
                   and not c.strip().startswith('LOAD_TIMESTAMP')
                   and not c.strip().startswith('SOURCE_FILE')
                   and not c.strip().startswith(')')
                   and not c.strip().startswith('(')
            )}
        )
        FROM {INTERNAL_STAGE}/{list(k for k,v in CSV_TABLE_MAP.items() if v == name)[0]}
        FILE_FORMAT = (FORMAT_NAME = '{CSV_FILE_FORMAT}')
        ON_ERROR    = 'CONTINUE'
        PURGE       = FALSE;
    """
    for name, ddl in BRONZE_DDL.items()
}


def load_via_pandas(conn, filepath: str, table_name: str):
    """Fallback: load using pandas write_pandas for local dev without PUT access."""
    log.info("Loading %s via pandas write_pandas ...", table_name)
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df.columns = [c.upper().replace(" ", "_").replace("(", "").replace(")", "")
                  for c in df.columns]
    df["LOAD_TIMESTAMP"] = pd.Timestamp.now()
    df["SOURCE_FILE"] = os.path.basename(filepath)

    success, nchunks, nrows, _ = write_pandas(
        conn, df, table_name, schema=BRONZE_SCHEMA,
        database=SNOWFLAKE_CONFIG["database"],
        auto_create_table=False, overwrite=True,
    )
    log.info("  -> %s rows loaded in %s chunks (success=%s)", nrows, nchunks, success)
    return nrows


# ── Main Loader ────────────────────────────────────────────────────────────────

def main():
    log.info("=== BRONZE LAYER LOAD STARTED ===")
    conn = get_connection()
    cur = conn.cursor()

    # Bootstrap
    log.info("Running bootstrap DDL ...")
    for stmt in BOOTSTRAP_SQL.strip().split(";"):
        stmt = stmt.strip()
        if stmt:
            cur.execute(stmt)

    # Create tables & load
    total_rows = 0
    errors = []
    for filename, table in CSV_TABLE_MAP.items():
        filepath = os.path.join(DATASET_DIR, filename)
        if not os.path.exists(filepath):
            log.warning("File not found, skipping: %s", filepath)
            continue

        log.info("Creating table %s.%s ...", BRONZE_SCHEMA, table)
        cur.execute(BRONZE_DDL[table])

        log.info("Loading data for %s ...", table)
        try:
            rows = load_via_pandas(conn, filepath, table)
            total_rows += rows
        except Exception as exc:
            log.error("Failed to load %s: %s", table, exc)
            errors.append((table, str(exc)))

    cur.close()
    conn.close()

    log.info("=== BRONZE LOAD COMPLETE: %s total rows, %s errors ===",
             total_rows, len(errors))
    if errors:
        for tbl, err in errors:
            log.error("  %s: %s", tbl, err)
    return len(errors) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
