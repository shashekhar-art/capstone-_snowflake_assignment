"""
Bronze Layer - Data Profiling Script
Analyzes source CSV files and Snowflake bronze tables for data quality issues
before and after ingestion.
"""
import os
import csv
import json
from datetime import datetime
import snowflake.connector
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config.snowflake_config import SNOWFLAKE_CONFIG, BRONZE_SCHEMA, CSV_TABLE_MAP


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_connection():
    cfg = dict(SNOWFLAKE_CONFIG)
    cfg["schema"] = BRONZE_SCHEMA
    return snowflake.connector.connect(**cfg)


def profile_csv(filepath: str) -> dict:
    """Return row count, column names, null counts, and sample rows for a CSV."""
    with open(filepath, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    total_rows = len(rows)
    null_counts = {h: 0 for h in headers}
    for row in rows:
        for h in headers:
            val = row.get(h, "")
            if val is None or val.strip() == "":
                null_counts[h] += 1

    return {
        "total_rows":  total_rows,
        "columns":     headers,
        "null_counts": null_counts,
        "null_pct":    {h: round(null_counts[h] / total_rows * 100, 2)
                        if total_rows else 0 for h in headers},
        "sample_rows": rows[:3],
    }


def profile_bronze_table(conn, table_name: str) -> dict:
    """Profile a bronze table in Snowflake."""
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) FROM {BRONZE_SCHEMA}.{table_name}")
    row_count = cur.fetchone()[0]

    cur.execute(f"SHOW COLUMNS IN TABLE {BRONZE_SCHEMA}.{table_name}")
    columns = [r[2] for r in cur.fetchall()]

    null_counts = {}
    for col in columns:
        cur.execute(
            f"SELECT COUNT(*) FROM {BRONZE_SCHEMA}.{table_name} "
            f"WHERE {col} IS NULL OR TRIM(CAST({col} AS VARCHAR)) = ''"
        )
        null_counts[col] = cur.fetchone()[0]

    cur.execute(f"SELECT * FROM {BRONZE_SCHEMA}.{table_name} LIMIT 3")
    sample = cur.fetchall()
    cur.close()

    return {
        "table":       table_name,
        "row_count":   row_count,
        "columns":     columns,
        "null_counts": null_counts,
        "sample_rows": sample,
    }


def detect_duplicates(conn, table_name: str, key_cols: list) -> int:
    """Return number of duplicate records based on key columns."""
    key_expr = ", ".join(key_cols)
    cur = conn.cursor()
    cur.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT {key_expr}, COUNT(*) AS cnt
            FROM {BRONZE_SCHEMA}.{table_name}
            GROUP BY {key_expr}
            HAVING cnt > 1
        )
    """)
    result = cur.fetchone()[0]
    cur.close()
    return result


# ── Main Profiling Run ─────────────────────────────────────────────────────────

def run_csv_profiling(dataset_dir: str):
    print("\n" + "=" * 60)
    print("  BRONZE LAYER - CSV PROFILING REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    report = {}
    for filename in sorted(os.listdir(dataset_dir)):
        if not filename.endswith(".csv"):
            continue
        filepath = os.path.join(dataset_dir, filename)
        profile = profile_csv(filepath)
        report[filename] = profile

        print(f"\n[FILE] {filename}")
        print(f"  Rows    : {profile['total_rows']:,}")
        print(f"  Columns : {len(profile['columns'])}")
        high_null = {c: p for c, p in profile["null_pct"].items() if p > 0}
        if high_null:
            print("  Null %  :")
            for col, pct in high_null.items():
                print(f"    {col:<35} {pct:>6.2f}%")
        else:
            print("  Null %  : No nulls detected")

    return report


def run_bronze_profiling(conn):
    print("\n" + "=" * 60)
    print("  BRONZE LAYER - SNOWFLAKE TABLE PROFILING REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    duplicate_key_map = {
        "BRONZE_SALES_2020":   ["ORDERNUMBER", "ORDERLINEITEM"],
        "BRONZE_SALES_2021":   ["ORDERNUMBER", "ORDERLINEITEM"],
        "BRONZE_SALES_2022":   ["ORDERNUMBER", "ORDERLINEITEM"],
        "BRONZE_CUSTOMER":     ["CUSTOMERKEY"],
        "BRONZE_PRODUCT":      ["PRODUCTKEY"],
        "BRONZE_TERRITORY":    ["SALESTERRITORYKEY"],
        "BRONZE_CALENDAR":     ["DATE"],
        "BRONZE_RETURNS":      ["RETURNDATE", "PRODUCTKEY", "TERRITORYKEY"],
        "BRONZE_PRODUCT_CATEGORY": ["PRODUCTCATEGORYKEY"],
        "BRONZE_SUBCATEGORY":  ["PRODUCTSUBCATEGORYKEY"],
    }

    for table in CSV_TABLE_MAP.values():
        try:
            profile = profile_bronze_table(conn, table)
            dupes = 0
            if table in duplicate_key_map:
                dupes = detect_duplicates(conn, table, duplicate_key_map[table])
            print(f"\n[TABLE] {BRONZE_SCHEMA}.{table}")
            print(f"  Row count  : {profile['row_count']:,}")
            print(f"  Duplicates : {dupes}")
        except Exception as exc:
            print(f"\n[TABLE] {table}  -- SKIPPED: {exc}")


def main():
    dataset_dir = os.path.join(
        os.path.dirname(__file__), "..", "capstone_project_dataset"
    )
    run_csv_profiling(dataset_dir)

    print("\n\nConnecting to Snowflake for table profiling...")
    try:
        conn = get_connection()
        run_bronze_profiling(conn)
        conn.close()
    except Exception as exc:
        print(f"Snowflake connection failed: {exc}")
        print("Run load_to_bronze.py first to create bronze tables.")


if __name__ == "__main__":
    main()
