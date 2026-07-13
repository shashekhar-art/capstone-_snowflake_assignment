# Adventure Works — Snowflake Capstone Project

**GitHub:** https://github.com/shashekhar-art/capstone-_snowflake_assignment  
**Snowflake Account:** uq57089.ap-southeast-7.aws  
**App URL:** https://app.snowflake.com/ap-southeast-7.aws/uq57089  
**Database:** `ADVENTURE_WORKS_DB`

---

## Project Overview

End-to-end Snowflake data engineering project using the **Adventure Works** retail dataset.  
Implements a **Medallion Architecture** (Bronze → Silver → Gold) with a **Star Schema** data mart, RBAC, dynamic data masking, clustering, and analytical views.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                      SOURCE LAYER                                     │
│  11 CSV files (Sales 2020/21/22, Customer, Product, Territory, etc.)  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │  PUT + COPY INTO / pandas write_pandas
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│              BRONZE  (ADVENTURE_WORKS_DB.BRONZE)                      │
│  Raw ingestion — VARCHAR/NUMBER, no transformations, LOAD_TIMESTAMP   │
│  11 tables  ·  load_to_bronze.py  ·  profiling.py                    │
└──────────────────────┬───────────────────────────────────────────────┘
                       │  CTAS with type-casting & derived columns
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│              SILVER  (ADVENTURE_WORKS_DB.SILVER)                      │
│  Typed · Cleansed · Enriched  (DATE casts, INITCAP, INCOME_BAND …)   │
│  8 tables  ·  transform_to_silver.py                                  │
└──────────────────────┬───────────────────────────────────────────────┘
                       │  CTAS joining Silver tables
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│              GOLD  (ADVENTURE_WORKS_DB.GOLD)  — Star Schema           │
│  4 Dimensions: DIM_DATE · DIM_CUSTOMER · DIM_PRODUCT · DIM_TERRITORY │
│  2 Facts:      FACT_SALES · FACT_RETURNS                              │
│  6 Views + 1 MV · load_dimensional.py · load_facts.py                │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
assignment/
├── capstone_project_dataset/          # Source CSV files (11 files)
│   ├── Sales Data 2020.csv
│   ├── Sales Data 2021.csv
│   ├── Sales Data 2022.csv
│   ├── Customer Lookup.csv
│   ├── Product Lookup.csv
│   ├── Product Categories Lookup.csv
│   ├── Subcategories Lookup.csv
│   ├── Calendar Lookup.csv
│   ├── Territory Lookup.csv
│   ├── Returns Data.csv
│   └── Product Category Sales (Unpivot Demo).csv
│
├── config/
│   └── snowflake_config.py            # Connection params + helpers
│
├── bronze_scripts/
│   ├── profiling.py                   # CSV + table data quality profiling
│   └── load_to_bronze.py              # Load CSVs → BRONZE schema
│
├── silver_scripts/
│   └── transform_to_silver.py         # BRONZE → SILVER (CTAS transforms)
│
├── gold_scripts/
│   ├── load_dimensional.py            # Build DIM_DATE/CUSTOMER/PRODUCT/TERRITORY
│   └── load_facts.py                  # Build FACT_SALES/RETURNS + DQ checks
│
├── sql/
│   ├── ddl/
│   │   ├── bronze_table.sql           # Bronze DDL (CREATE TABLE statements)
│   │   ├── silver_table.sql           # Silver DDL
│   │   └── gold_table.sql             # Gold DDL + PK/FK constraints
│   ├── queries/
│   │   └── analytics_queries.sql      # 12 business queries (revenue, CLV, etc.)
│   ├── views/
│   │   └── analytical_views.sql       # 5 views + 1 materialized view
│   ├── optimization/
│   │   └── clustering.sql             # Cluster keys, search optimization, MV
│   └── security/
│       ├── rbac.sql                   # Roles, grants, users
│       └── masking_policies.sql       # Dynamic masking + row access policy
│
├── exports/
│   └── export_reports.py             # Generate Excel + PDF reports from Snowflake
│
├── documentation/
│   ├── diagrams/                      # Architecture diagrams
│   ├── data_dictionary.md             # Full column-level data dictionary
│   └── governance.md                  # RBAC, masking, retention, ETL order
│
├── README.md                          # This file
└── .gitignore
```

---

## Quick Start

### Prerequisites
```bash
pip install snowflake-connector-python snowflake-snowpark-python pandas \
            openpyxl xlsxwriter reportlab python-dotenv
```

### 1. Configure Connection
```bash
# Option A: use .env file (recommended)
cp .env.example .env
# edit .env with your credentials

# Option B: set environment variables directly
export SNOWFLAKE_ACCOUNT="uq57089.ap-southeast-7.aws"
export SNOWFLAKE_USER="shashekhar"
export SNOWFLAKE_PASSWORD="<password>"
```

### 2. Run ETL Pipeline (in order)
```bash
# Step 1 — Bootstrap database + load CSVs to Bronze
python bronze_scripts/load_to_bronze.py

# Step 2 — Profile Bronze data quality
python bronze_scripts/profiling.py

# Step 3 — Transform Bronze → Silver
python silver_scripts/transform_to_silver.py

# Step 4 — Build Gold dimensions
python gold_scripts/load_dimensional.py

# Step 5 — Build Gold facts + run DQ checks
python gold_scripts/load_facts.py
```

### 3. Apply SQL Objects (via Snowflake UI or SnowSQL)
```sql
-- Run in order:
-- 1. sql/views/analytical_views.sql
-- 2. sql/security/rbac.sql
-- 3. sql/security/masking_policies.sql
-- 4. sql/optimization/clustering.sql
```

### 4. Generate Reports
```bash
python exports/export_reports.py
# Output: exports/output/adventure_works_report.xlsx
#         exports/output/adventure_works_summary.pdf
```

---

## Key Business Queries

| # | Query | File |
|---|---|---|
| Q1 | Sales summary by year | analytics_queries.sql |
| Q2 | Monthly revenue trend with MoM growth | analytics_queries.sql |
| Q3 | Revenue by product category & subcategory | analytics_queries.sql |
| Q4 | Top 10 best-selling products | analytics_queries.sql |
| Q5 | Customer segmentation (income, occupation, gender) | analytics_queries.sql |
| Q6 | Revenue by geography | analytics_queries.sql |
| Q7 | Return rate by product | analytics_queries.sql |
| Q8 | Quarterly revenue with YoY comparison | analytics_queries.sql |
| Q9 | Customer Lifetime Value — Top 20 | analytics_queries.sql |
| Q10 | Product category sales unpivot | analytics_queries.sql |
| Q11 | Weekend vs Weekday sales pattern | analytics_queries.sql |
| Q12 | Running YTD revenue by year | analytics_queries.sql |

---

## Git Workflow

### Branch Strategy
```bash
main          # production-ready
  └── develop  # integration
        ├── feature/bronze-load
        ├── feature/silver-transform
        └── feature/gold-schema
```

### Typical Feature Workflow
```bash
git checkout develop
git pull origin develop
git checkout -b feature/my-feature
# ... make changes ...
git add <files>
git commit -m "feat: describe the change"
git push origin feature/my-feature
# Open Pull Request → develop
```

### Merge Conflict Resolution
```bash
git fetch origin
git merge origin/develop
# If conflicts appear, edit conflicted files, then:
git add <resolved-files>
git commit -m "resolve: merge conflict in <file>"
```

### Undo & Recovery
```bash
# Undo last commit (keep changes staged)
git reset --soft HEAD~1

# Discard changes to a file
git checkout -- <file>

# Recover deleted branch
git reflog
git checkout -b <branch> <commit-hash>

# Revert a pushed commit
git revert <commit-hash>
git push origin <branch>
```

---

## Data Quality Checks

Bronze: `python bronze_scripts/profiling.py`  
Gold: DQ checks run automatically in `load_facts.py`

Expected outputs after full load:
- FACT_SALES: ~42,000 rows
- FACT_RETURNS: ~1,800 rows
- DIM_CUSTOMER: ~18,500 rows
- DIM_PRODUCT: ~294 rows
- DIM_DATE: ~1,100 rows
- DIM_TERRITORY: 10 rows

---

## Security Notes

- All credentials should be stored in environment variables or `.env` (never commit `.env`)
- The `.gitignore` excludes `.env`, `*.pyc`, `__pycache__/`, output files
- See `documentation/governance.md` for full masking policy details
- See `sql/security/rbac.sql` for role definitions
