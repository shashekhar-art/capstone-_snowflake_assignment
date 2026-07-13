"""
Snowflake Connection Configuration
Capstone Project - Adventure Works Sales Analytics
Account : uq57089.ap-southeast-7.aws
App URL : https://app.snowflake.com/ap-southeast-7.aws/uq57089
"""
import os
from dotenv import load_dotenv

load_dotenv()   # loads .env if present; env vars always win over defaults

# ── Connection Parameters ──────────────────────────────────────────────────────
SNOWFLAKE_CONFIG = {
    "account":   os.getenv("SNOWFLAKE_ACCOUNT",   "uq57089.ap-southeast-7.aws"),
    "user":      os.getenv("SNOWFLAKE_USER",       "shashekhar"),
    "password":  os.getenv("SNOWFLAKE_PASSWORD",   "Sha@rock@54321"),
    "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE",  "COMPUTE_WH"),
    "database":  os.getenv("SNOWFLAKE_DATABASE",   "ADVENTURE_WORKS_DB"),
    "role":      os.getenv("SNOWFLAKE_ROLE",        "SYSADMIN"),
}

# ── Medallion Layer Schemas ────────────────────────────────────────────────────
BRONZE_SCHEMA = "BRONZE"
SILVER_SCHEMA = "SILVER"
GOLD_SCHEMA   = "GOLD"

# ── Internal Stage ─────────────────────────────────────────────────────────────
INTERNAL_STAGE = "@ADVENTURE_WORKS_DB.BRONZE.RAW_DATA_STAGE"

# ── File Format ────────────────────────────────────────────────────────────────
CSV_FILE_FORMAT = "ADVENTURE_WORKS_DB.BRONZE.CSV_FORMAT"

# ── Source CSV Mappings ────────────────────────────────────────────────────────
# Maps each source file to its target bronze table
CSV_TABLE_MAP = {
    "Sales Data 2020.csv":                        "BRONZE_SALES_2020",
    "Sales Data 2021.csv":                        "BRONZE_SALES_2021",
    "Sales Data 2022.csv":                        "BRONZE_SALES_2022",
    "Customer Lookup.csv":                        "BRONZE_CUSTOMER",
    "Product Lookup.csv":                         "BRONZE_PRODUCT",
    "Product Categories Lookup.csv":              "BRONZE_PRODUCT_CATEGORY",
    "Subcategories Lookup.csv":                   "BRONZE_SUBCATEGORY",
    "Calendar Lookup.csv":                        "BRONZE_CALENDAR",
    "Territory Lookup.csv":                       "BRONZE_TERRITORY",
    "Returns Data.csv":                           "BRONZE_RETURNS",
    "Product Category Sales (Unpivot Demo).csv":  "BRONZE_CATEGORY_SALES_UNPIVOT",
}

# ── Warehouse Sizes ────────────────────────────────────────────────────────────
WH_SIZE_PROFILING  = "X-SMALL"
WH_SIZE_LOADING    = "X-LARGE" # perf-team: upgrade to X-LARGE for 2022 full-year backfill
WH_SIZE_TRANSFORM  = "MEDIUM"
WH_SIZE_ANALYTICS  = "LARGE"


# ── Connection Helpers ─────────────────────────────────────────────────────────
def get_connection(schema: str = None):
    """Return an open SnowflakeConnection, optionally overriding the schema."""
    import snowflake.connector
    cfg = {**SNOWFLAKE_CONFIG}
    if schema:
        cfg["schema"] = schema
    return snowflake.connector.connect(**cfg)


def execute_sql(sql: str, schema: str = None, params=None):
    """Execute a single SQL statement and return rows as list-of-dicts."""
    from snowflake.connector import DictCursor
    conn = get_connection(schema)
    cur  = conn.cursor(DictCursor)
    try:
        cur.execute(sql, params or ())
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def execute_sql_file(file_path: str, schema: str = None):
    """Execute every semicolon-delimited statement in a .sql file."""
    with open(file_path, "r", encoding="utf-8") as fh:
        raw = fh.read()
    stmts = [s.strip() for s in raw.split(";") if s.strip()]
    conn  = get_connection(schema)
    cur   = conn.cursor()
    try:
        for stmt in stmts:
            cur.execute(stmt)
        conn.commit()
    finally:
        cur.close()
        conn.close()


def test_connection() -> bool:
    """Quick connectivity smoke-test."""
    try:
        rows = execute_sql(
            "SELECT CURRENT_USER() AS u, CURRENT_ACCOUNT() AS a, "
            "CURRENT_WAREHOUSE() AS w, CURRENT_DATABASE() AS d"
        )
        print(f"[OK] user={rows[0]['U']}  account={rows[0]['A']}  "
              f"wh={rows[0]['W']}  db={rows[0]['D']}")
        return True
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return False


if __name__ == "__main__":
    test_connection()
