# Data Governance — Adventure Works Capstone Project

**Account:** uq57089.ap-southeast-7.aws  
**Platform:** Snowflake Enterprise  
**Owner:** shashekhar@deloitte.com

---

## 1. Role Hierarchy

```
SYSADMIN (Snowflake system)
    └── CAPSTONE_SYSADMIN          ← Full project admin
            ├── CAPSTONE_DATA_ENGINEER   ← ETL pipelines; full BRONZE + SILVER DML
            ├── CAPSTONE_ANALYST         ← Read-only GOLD tables + views
            └── CAPSTONE_VIEWER          ← Read-only GOLD views only (masked PII)
```

| Role | Tables | Masking | Use Case |
|---|---|---|---|
| CAPSTONE_SYSADMIN | ALL (DDL + DML) | None | Platform admin |
| CAPSTONE_DATA_ENGINEER | BRONZE + SILVER (DML), GOLD (DML) | None — full PII | ETL service accounts |
| CAPSTONE_ANALYST | GOLD (SELECT), SILVER (SELECT) | Partial mask | Data analysts |
| CAPSTONE_VIEWER | GOLD views only (SELECT) | Full mask | Business stakeholders |

---

## 2. Data Masking Policies

All policies are defined in `sql/security/masking_policies.sql` and applied to `ADVENTURE_WORKS_DB.GOLD.DIM_CUSTOMER`.

### MASK_EMAIL_ADDRESS

| Role | Result |
|---|---|
| CAPSTONE_SYSADMIN / CAPSTONE_DATA_ENGINEER | `jon24@adventure-works.com` (full) |
| CAPSTONE_ANALYST | `j***@adventure-works.com` |
| CAPSTONE_VIEWER | `***@***.com` |

### MASK_FULL_NAME

| Role | Result |
|---|---|
| CAPSTONE_SYSADMIN / CAPSTONE_DATA_ENGINEER | `Jon Yang` |
| CAPSTONE_ANALYST | `Jon Y.` |
| CAPSTONE_VIEWER | `J.Y.` |

### MASK_ANNUAL_INCOME

| Role | Result |
|---|---|
| CAPSTONE_SYSADMIN / CAPSTONE_DATA_ENGINEER | `90000` (exact) |
| CAPSTONE_ANALYST | `90000` (rounded to nearest $10K) |
| CAPSTONE_VIEWER | `0` (use INCOME_BAND column instead) |

### MASK_BIRTH_DATE

| Role | Result |
|---|---|
| CAPSTONE_SYSADMIN / CAPSTONE_DATA_ENGINEER | `1966-04-08` |
| CAPSTONE_ANALYST | `1966-01-01` (year only) |
| CAPSTONE_VIEWER | `NULL` |

---

## 3. Row Access Policy

**Policy:** `RAP_TERRITORY_FILTER` on `FACT_SALES.TERRITORY_KEY`

- CAPSTONE_SYSADMIN, CAPSTONE_DATA_ENGINEER, CAPSTONE_ANALYST → see **all** territories
- CAPSTONE_VIEWER → see **only** territories assigned in `USER_TERRITORY_ACCESS` mapping table

```sql
-- Example: limit VIEWER_USER to territories 1, 2, 3
INSERT INTO ADVENTURE_WORKS_DB.GOLD.USER_TERRITORY_ACCESS VALUES
    ('VIEWER_USER', 1), ('VIEWER_USER', 2), ('VIEWER_USER', 3);
```

---

## 4. PII Inventory

| Table | Column | PII Category | Masking Applied |
|---|---|---|---|
| SILVER_CUSTOMER / DIM_CUSTOMER | EMAIL_ADDRESS | Contact info | MASK_EMAIL_ADDRESS |
| SILVER_CUSTOMER / DIM_CUSTOMER | FULL_NAME | Identity | MASK_FULL_NAME |
| SILVER_CUSTOMER / DIM_CUSTOMER | ANNUAL_INCOME | Financial | MASK_ANNUAL_INCOME |
| SILVER_CUSTOMER / DIM_CUSTOMER | BIRTH_DATE | Demographic | MASK_BIRTH_DATE |
| BRONZE_CUSTOMER | EMAILADDRESS | Contact info | No mask (raw layer — restrict by role) |

---

## 5. Data Quality Controls

### Bronze Layer Checks (profiling.py)
- Row count per CSV vs loaded table
- Null percentage per column
- Duplicate detection on natural keys

### Gold Layer Checks (load_facts.py)
| Check | Expected | Action |
|---|---|---|
| Orphaned PRODUCT_KEY in FACT_SALES | 0 | Investigate source gap |
| Orphaned CUSTOMER_KEY in FACT_SALES | 0 | Investigate source gap |
| Orphaned TERRITORY_KEY in FACT_SALES | 0 | Investigate source gap |
| Negative GROSS_REVENUE | 0 | Review product pricing |
| NULL ORDER_DATE_KEY | 0 | Check Bronze date parsing |

---

## 6. Retention & Lifecycle Policy

| Layer | Retention | Reason |
|---|---|---|
| BRONZE | 90 days Time Travel (max 90d Enterprise) | Reprocessing & audit |
| SILVER | 30 days Time Travel | Transformation rerun |
| GOLD | 14 days Time Travel | BI rollback window |
| Stage files | Purge after successful COPY | Storage cost control |

### Snowflake Time Travel Commands
```sql
-- Restore SILVER_SALES to state 2 hours ago
CREATE OR REPLACE TABLE ADVENTURE_WORKS_DB.SILVER.SILVER_SALES
    CLONE ADVENTURE_WORKS_DB.SILVER.SILVER_SALES AT (OFFSET => -7200);

-- View FACT_SALES data as of a specific timestamp
SELECT * FROM ADVENTURE_WORKS_DB.GOLD.FACT_SALES
AT (TIMESTAMP => '2026-07-12 09:00:00'::TIMESTAMP_NTZ);
```

---

## 7. ETL Run Order

Always execute in this sequence to respect layer dependencies:

```
1. sql/ddl/bronze_table.sql          ← Create Bronze schema + tables
2. bronze_scripts/load_to_bronze.py  ← Load CSVs → Bronze
3. bronze_scripts/profiling.py       ← Validate Bronze row counts & nulls
4. sql/ddl/silver_table.sql          ← Create Silver schema + tables
5. silver_scripts/transform_to_silver.py ← Bronze → Silver
6. sql/ddl/gold_table.sql            ← Create Gold schema + tables
7. gold_scripts/load_dimensional.py  ← Silver → Gold Dimensions
8. gold_scripts/load_facts.py        ← Silver + Gold Dims → Gold Facts
9. sql/views/analytical_views.sql    ← Create analytical views
10. sql/security/rbac.sql            ← Apply RBAC
11. sql/security/masking_policies.sql ← Apply masking
12. sql/optimization/clustering.sql  ← Set cluster keys
```

---

## 8. Warehouse Strategy

| Warehouse | Size | Purpose | Auto-Suspend |
|---|---|---|---|
| COMPUTE_WH | SMALL | Default/ETL loading | 60s |
| CAPSTONE_ANALYTICS_WH | MEDIUM (multi-cluster 1-3) | BI tool queries | 120s |
| CAPSTONE_ETL_WH | LARGE | Heavy transforms | 60s |

---

## 9. Branching & Deployment Strategy (Git)

| Branch | Purpose | Merge Target |
|---|---|---|
| `main` | Production-ready code | — |
| `develop` | Integration branch | `main` via PR |
| `feature/bronze-load` | Bronze layer development | `develop` |
| `feature/silver-transform` | Silver layer development | `develop` |
| `feature/gold-schema` | Gold layer development | `develop` |
| `hotfix/critical-fix` | Production bug fixes | `main` + `develop` |

---

## 10. Sensitive Data Classification

| Classification | Description | Snowflake Action |
|---|---|---|
| RESTRICTED | PII: name, email, DOB, income | Dynamic masking + role restriction |
| CONFIDENTIAL | Financial: revenue, profit, margin | Role-based access (Analyst+) |
| INTERNAL | Aggregated metrics, KPIs | Available to all roles |
| PUBLIC | Territory names, category labels | No restriction |
# temp note added for revert demo
