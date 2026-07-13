"""
Gold Layer - Load Fact Tables (Star Schema)
Builds FACT_SALES and FACT_RETURNS with degenerate dimensions and metrics.

Fact tables created:
  FACT_SALES   - Grain: one row per order line item
  FACT_RETURNS - Grain: one row per return record
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


# ── Fact Table DDL + Populate ──────────────────────────────────────────────────

FACT_SALES = """
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.GOLD.FACT_SALES AS
SELECT
    -- Surrogate key (degenerate)
    s.ORDER_NUMBER                              AS ORDER_NUMBER,
    s.ORDER_LINE_ITEM                           AS ORDER_LINE_ITEM,

    -- Foreign keys to dimensions
    s.ORDER_DATE                                AS ORDER_DATE_KEY,
    s.PRODUCT_KEY,
    s.CUSTOMER_KEY,
    s.TERRITORY_KEY,

    -- Degenerate dimensions
    s.STOCK_DATE                                AS STOCK_DATE_KEY,
    s.SALES_YEAR,

    -- Additive measures
    s.ORDER_QUANTITY,
    COALESCE(p.PRODUCT_PRICE, 0)                AS UNIT_PRICE,
    COALESCE(p.PRODUCT_COST,  0)                AS UNIT_COST,
    ROUND(s.ORDER_QUANTITY * COALESCE(p.PRODUCT_PRICE, 0), 2) AS GROSS_REVENUE,
    ROUND(s.ORDER_QUANTITY * COALESCE(p.PRODUCT_COST,  0), 2) AS TOTAL_COST,
    ROUND(
        s.ORDER_QUANTITY * COALESCE(p.PRODUCT_PRICE, 0) -
        s.ORDER_QUANTITY * COALESCE(p.PRODUCT_COST,  0),
    2)                                          AS GROSS_PROFIT,
    ROUND(COALESCE(p.MARGIN_PCT, 0), 2)         AS MARGIN_PCT,

    -- Days from stock to order (lead time)
    s.DAYS_FROM_STOCK_TO_ORDER                  AS LEAD_TIME_DAYS,

    -- Audit
    CURRENT_TIMESTAMP()                         AS LOAD_TIMESTAMP

FROM ADVENTURE_WORKS_DB.SILVER.SILVER_SALES s
LEFT JOIN ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT p
       ON s.PRODUCT_KEY = p.PRODUCT_KEY;
"""

FACT_RETURNS = """
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.GOLD.FACT_RETURNS AS
SELECT
    r.RETURN_DATE                               AS RETURN_DATE_KEY,
    r.PRODUCT_KEY,
    r.TERRITORY_KEY,
    r.RETURN_QUANTITY,
    COALESCE(p.PRODUCT_PRICE, 0)                AS UNIT_PRICE,
    ROUND(r.RETURN_QUANTITY * COALESCE(p.PRODUCT_PRICE, 0), 2) AS RETURN_REVENUE_IMPACT,
    CURRENT_TIMESTAMP()                         AS LOAD_TIMESTAMP
FROM ADVENTURE_WORKS_DB.SILVER.SILVER_RETURNS r
LEFT JOIN ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT p
       ON r.PRODUCT_KEY = p.PRODUCT_KEY;
"""

# ── Foreign Key Constraints (informational, not enforced) ─────────────────────

FK_SQL = [
    "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_SALES ADD FOREIGN KEY (PRODUCT_KEY)   REFERENCES ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT(PRODUCT_KEY)     RELY NOVALIDATE;",
    "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_SALES ADD FOREIGN KEY (CUSTOMER_KEY)  REFERENCES ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER(CUSTOMER_KEY)    RELY NOVALIDATE;",
    "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_SALES ADD FOREIGN KEY (TERRITORY_KEY) REFERENCES ADVENTURE_WORKS_DB.GOLD.DIM_TERRITORY(TERRITORY_KEY)  RELY NOVALIDATE;",
    "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_SALES ADD FOREIGN KEY (ORDER_DATE_KEY) REFERENCES ADVENTURE_WORKS_DB.GOLD.DIM_DATE(DATE_KEY)           RELY NOVALIDATE;",
    "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_RETURNS ADD FOREIGN KEY (PRODUCT_KEY)  REFERENCES ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT(PRODUCT_KEY)     RELY NOVALIDATE;",
    "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_RETURNS ADD FOREIGN KEY (TERRITORY_KEY) REFERENCES ADVENTURE_WORKS_DB.GOLD.DIM_TERRITORY(TERRITORY_KEY) RELY NOVALIDATE;",
    "ALTER TABLE ADVENTURE_WORKS_DB.GOLD.FACT_RETURNS ADD FOREIGN KEY (RETURN_DATE_KEY) REFERENCES ADVENTURE_WORKS_DB.GOLD.DIM_DATE(DATE_KEY)        RELY NOVALIDATE;",
]

# ── Data Quality Checks ────────────────────────────────────────────────────────

DQ_CHECKS = [
    ("Orphaned PRODUCT_KEY in FACT_SALES",
     "SELECT COUNT(*) FROM ADVENTURE_WORKS_DB.GOLD.FACT_SALES f "
     "LEFT JOIN ADVENTURE_WORKS_DB.GOLD.DIM_PRODUCT p ON f.PRODUCT_KEY = p.PRODUCT_KEY "
     "WHERE p.PRODUCT_KEY IS NULL"),
    ("Orphaned CUSTOMER_KEY in FACT_SALES",
     "SELECT COUNT(*) FROM ADVENTURE_WORKS_DB.GOLD.FACT_SALES f "
     "LEFT JOIN ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER c ON f.CUSTOMER_KEY = c.CUSTOMER_KEY "
     "WHERE c.CUSTOMER_KEY IS NULL"),
    ("Orphaned TERRITORY_KEY in FACT_SALES",
     "SELECT COUNT(*) FROM ADVENTURE_WORKS_DB.GOLD.FACT_SALES f "
     "LEFT JOIN ADVENTURE_WORKS_DB.GOLD.DIM_TERRITORY t ON f.TERRITORY_KEY = t.TERRITORY_KEY "
     "WHERE t.TERRITORY_KEY IS NULL"),
    ("Negative GROSS_REVENUE in FACT_SALES",
     "SELECT COUNT(*) FROM ADVENTURE_WORKS_DB.GOLD.FACT_SALES WHERE GROSS_REVENUE < 0"),
    ("NULL ORDER_DATE_KEY in FACT_SALES",
     "SELECT COUNT(*) FROM ADVENTURE_WORKS_DB.GOLD.FACT_SALES WHERE ORDER_DATE_KEY IS NULL"),
]


def run_dq_checks(conn):
    log.info("Running data quality checks ...")
    cur = conn.cursor()
    all_passed = True
    for name, sql in DQ_CHECKS:
        cur.execute(sql)
        count = cur.fetchone()[0]
        status = "PASS" if count == 0 else f"WARN ({count:,} records)"
        log.info("  DQ %-50s %s", name, status)
        if count > 0:
            all_passed = False
    cur.close()
    return all_passed


def main():
    log.info("=== GOLD LAYER - FACT LOAD STARTED ===")
    conn = get_connection()
    cur = conn.cursor()

    for fact_name, sql in [("FACT_SALES", FACT_SALES), ("FACT_RETURNS", FACT_RETURNS)]:
        log.info("Building %s ...", fact_name)
        start = datetime.now()
        try:
            cur.execute(sql)
            cur.execute(f"SELECT COUNT(*) FROM ADVENTURE_WORKS_DB.GOLD.{fact_name}")
            rows = cur.fetchone()[0]
            elapsed = (datetime.now() - start).total_seconds()
            log.info("  %-20s -> %8s rows  (%.1fs)", fact_name, f"{rows:,}", elapsed)
        except Exception as exc:
            log.error("  FAILED %s: %s", fact_name, exc)

    log.info("Applying foreign key constraints ...")
    for fk in FK_SQL:
        try:
            cur.execute(fk)
        except Exception as exc:
            log.warning("  FK warning: %s", exc)

    cur.close()

    dq_passed = run_dq_checks(conn)
    conn.close()

    log.info("=== FACT LOAD COMPLETE | DQ: %s ===",
             "ALL PASSED" if dq_passed else "WARNINGS FOUND")


if __name__ == "__main__":
    main()
