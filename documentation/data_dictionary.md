# Data Dictionary — Adventure Works Capstone Project

**Snowflake Account:** `uq57089.ap-southeast-7.aws`  
**Database:** `ADVENTURE_WORKS_DB`  
**Architecture:** Medallion (Bronze → Silver → Gold)  
**Last Updated:** 2026-07-13

---

## Architecture Overview

```
Source CSVs (11 files)
        │
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  BRONZE Layer  (ADVENTURE_WORKS_DB.BRONZE)                       │
│  Raw ingestion — VARCHAR/NUMBER columns, no transformations      │
│  Tables: BRONZE_SALES_2020/21/22, BRONZE_CUSTOMER, BRONZE_PRODUCT│
│          BRONZE_TERRITORY, BRONZE_CALENDAR, BRONZE_RETURNS,      │
│          BRONZE_PRODUCT_CATEGORY, BRONZE_SUBCATEGORY,            │
│          BRONZE_CATEGORY_SALES_UNPIVOT                           │
└─────────────────────────────────────────────────────────────────┘
        │  profiling.py + load_to_bronze.py
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  SILVER Layer  (ADVENTURE_WORKS_DB.SILVER)                       │
│  Typed, cleansed, enriched — DATE casts, INITCAP, derived cols   │
│  Tables: SILVER_CALENDAR, SILVER_TERRITORY, SILVER_PRODUCT_CATEGORY│
│          SILVER_PRODUCT, SILVER_CUSTOMER, SILVER_SALES,          │
│          SILVER_RETURNS, SILVER_CATEGORY_SALES_UNPIVOT           │
└─────────────────────────────────────────────────────────────────┘
        │  transform_to_silver.py
        ▼
┌─────────────────────────────────────────────────────────────────┐
│  GOLD Layer  (ADVENTURE_WORKS_DB.GOLD)                           │
│  Star Schema — Dimensions + Facts + Views                        │
│  Dimensions: DIM_DATE, DIM_CUSTOMER, DIM_PRODUCT, DIM_TERRITORY  │
│  Facts:      FACT_SALES, FACT_RETURNS                            │
│  Views:      VW_SALES_DETAIL, VW_MONTHLY_KPI, VW_PRODUCT_PERF,  │
│              VW_CUSTOMER_360, VW_TERRITORY_SUMMARY, VW_RETURN_ANALYSIS│
└─────────────────────────────────────────────────────────────────┘
```

---

## Source Files

| File | Rows (approx.) | Target Bronze Table |
|---|---|---|
| Sales Data 2020.csv | ~14,000 | BRONZE_SALES_2020 |
| Sales Data 2021.csv | ~15,000 | BRONZE_SALES_2021 |
| Sales Data 2022.csv | ~13,000 | BRONZE_SALES_2022 |
| Customer Lookup.csv | ~18,500 | BRONZE_CUSTOMER |
| Product Lookup.csv | ~294 | BRONZE_PRODUCT |
| Product Categories Lookup.csv | 4 | BRONZE_PRODUCT_CATEGORY |
| Subcategories Lookup.csv | 37 | BRONZE_SUBCATEGORY |
| Calendar Lookup.csv | ~1,100 | BRONZE_CALENDAR |
| Territory Lookup.csv | 10 | BRONZE_TERRITORY |
| Returns Data.csv | ~1,800 | BRONZE_RETURNS |
| Product Category Sales (Unpivot Demo).csv | ~36 | BRONZE_CATEGORY_SALES_UNPIVOT |

---

## BRONZE Layer Tables

### BRONZE_SALES_2020 / BRONZE_SALES_2021 / BRONZE_SALES_2022

| Column | Type | Description |
|---|---|---|
| ORDERDATE | VARCHAR(20) | Order date as raw string (YYYY-MM-DD) |
| STOCKDATE | VARCHAR(20) | Stock replenishment date |
| ORDERNUMBER | VARCHAR(20) | Order identifier (e.g., SO45080) |
| PRODUCTKEY | NUMBER | Foreign key to product |
| CUSTOMERKEY | NUMBER | Foreign key to customer |
| TERRITORYKEY | NUMBER | Foreign key to territory |
| ORDERLINEITEM | NUMBER | Line item number within order |
| ORDERQUANTITY | NUMBER | Quantity ordered |
| LOAD_TIMESTAMP | TIMESTAMP_NTZ | ETL ingestion timestamp |
| SOURCE_FILE | VARCHAR(100) | Source CSV filename |

### BRONZE_CUSTOMER

| Column | Type | Description |
|---|---|---|
| CUSTOMERKEY | NUMBER | Customer natural key (11000–29483) |
| PREFIX | VARCHAR(10) | Title (MR., MS., DR., etc.) |
| FIRSTNAME | VARCHAR(50) | First name (uppercase in source) |
| LASTNAME | VARCHAR(50) | Last name (uppercase in source) |
| BIRTHDATE | VARCHAR(20) | Birth date as raw string |
| MARITALSTATUS | VARCHAR(5) | M = Married, S = Single |
| GENDER | VARCHAR(5) | M = Male, F = Female |
| EMAILADDRESS | VARCHAR(100) | Email address |
| ANNUALINCOME | NUMBER | Annual household income (USD) |
| TOTALCHILDREN | NUMBER | Total number of children |
| EDUCATIONLEVEL | VARCHAR(50) | Bachelors, High School, Partial College, Graduate Degree |
| OCCUPATION | VARCHAR(50) | Professional, Management, Skilled Manual, Manual, Clerical |
| HOMEOWNER | VARCHAR(5) | Y = owner, N = renter |

### BRONZE_PRODUCT

| Column | Type | Description |
|---|---|---|
| PRODUCTKEY | NUMBER | Product natural key (214–606) |
| PRODUCTSUBCATEGORYKEY | NUMBER | FK to subcategory |
| PRODUCTSKU | VARCHAR(20) | SKU code (e.g., HL-U509-R) |
| PRODUCTNAME | VARCHAR(200) | Full product name |
| MODELNAME | VARCHAR(100) | Model family name |
| PRODUCTDESCRIPTION | VARCHAR(500) | Marketing description |
| PRODUCTCOLOR | VARCHAR(30) | Color label or '0' for N/A |
| PRODUCTSIZE | VARCHAR(10) | Size code or '0' for N/A |
| PRODUCTSTYLE | VARCHAR(10) | Style code or '0' for N/A |
| PRODUCTCOST | NUMBER(12,4) | Unit cost (USD) |
| PRODUCTPRICE | NUMBER(12,4) | List price (USD) |

---

## SILVER Layer Tables

### SILVER_CALENDAR

| Column | Type | Description |
|---|---|---|
| DATE_KEY | DATE NOT NULL | Calendar date (natural PK) |
| YEAR | NUMBER(4) | Calendar year |
| MONTH_NUM | NUMBER(2) | Month number 1–12 |
| MONTH_NAME | VARCHAR(10) | January … December |
| DAY_OF_MONTH | NUMBER(2) | Day 1–31 |
| DAY_OF_WEEK_NAME | VARCHAR(10) | Monday … Sunday |
| DAY_OF_WEEK_NUM | NUMBER(1) | 0 = Sunday, 6 = Saturday |
| QUARTER_NUM | NUMBER(1) | Quarter 1–4 |
| QUARTER_NAME | VARCHAR(3) | Q1 … Q4 |
| WEEK_OF_YEAR | NUMBER(2) | ISO week 1–53 |
| IS_WEEKEND | BOOLEAN | TRUE for Saturday/Sunday |
| FIRST_DAY_OF_MONTH | DATE | First calendar day of month |
| LAST_DAY_OF_MONTH | DATE | Last calendar day of month |

### SILVER_CUSTOMER (key derived columns)

| Column | Type | Description |
|---|---|---|
| FULL_NAME | VARCHAR(101) | Derived: INITCAP(FirstName) + ' ' + INITCAP(LastName) |
| BIRTH_DATE | DATE | TRY_TO_DATE cast from VARCHAR |
| AGE | NUMBER(3) | DATEDIFF(years, BIRTH_DATE, CURRENT_DATE()) |
| MARITAL_STATUS | VARCHAR(10) | Expanded: M→Married, S→Single |
| GENDER | VARCHAR(10) | Expanded: M→Male, F→Female |
| INCOME_BAND | VARCHAR(15) | Low / Medium / High / Very High |
| IS_HOME_OWNER | BOOLEAN | HOMEOWNER='Y' → TRUE |

### SILVER_PRODUCT (key derived columns)

| Column | Type | Description |
|---|---|---|
| PRODUCT_COLOR | VARCHAR(30) | '0' replaced with 'Unknown' |
| PRODUCT_SIZE | VARCHAR(10) | '0' replaced with 'N/A' |
| GROSS_MARGIN | NUMBER(12,4) | PRODUCT_PRICE − PRODUCT_COST |
| MARGIN_PCT | NUMBER(7,2) | GROSS_MARGIN / PRODUCT_PRICE × 100 |
| SUBCATEGORY_NAME | VARCHAR(100) | Joined from BRONZE_SUBCATEGORY |
| CATEGORY_NAME | VARCHAR(50) | Joined from BRONZE_PRODUCT_CATEGORY |

### SILVER_SALES (consolidated 2020+2021+2022)

| Column | Type | Description |
|---|---|---|
| ORDER_NUMBER | VARCHAR(20) NOT NULL | Order identifier |
| ORDER_DATE | DATE | Cast from ORDERDATE VARCHAR |
| STOCK_DATE | DATE | Cast from STOCKDATE VARCHAR |
| DAYS_FROM_STOCK_TO_ORDER | NUMBER | DATEDIFF(day, STOCK_DATE, ORDER_DATE) |
| SALES_YEAR | NUMBER(4) | Source year literal (2020/2021/2022) |

---

## GOLD Layer — Star Schema

### DIM_DATE

| Column | Type | Key Attributes |
|---|---|---|
| DATE_KEY | DATE (PK) | Natural key |
| FISCAL_YEAR | NUMBER(4) | Year starting July 1 |
| FISCAL_QUARTER | VARCHAR(3) | FQ1 (Jul–Sep) … FQ4 (Apr–Jun) |
| IS_WEEKEND | BOOLEAN | Drives weekend vs weekday analysis |

### DIM_CUSTOMER

| Column | Type | Key Attributes |
|---|---|---|
| CUSTOMER_KEY | NUMBER (PK) | Natural key from source |
| INCOME_BAND | VARCHAR(15) | Segmentation: Low/Medium/High/Very High |
| AGE | NUMBER(3) | Derived at Silver → recalculated at Gold |

### DIM_PRODUCT

| Column | Type | Key Attributes |
|---|---|---|
| PRODUCT_KEY | NUMBER (PK) | Natural key from source |
| PRICE_TIER | VARCHAR(15) | Budget (<$50) / Mid-Range / Premium / Luxury (>$1000) |
| GROSS_MARGIN | NUMBER(12,4) | Pre-calculated for fact table join optimization |

### DIM_TERRITORY

| Column | Type | Key Attributes |
|---|---|---|
| TERRITORY_KEY | NUMBER (PK) | Natural key from source |
| REGION_CODE | VARCHAR(5) | Abbreviated: NW, NE, CTR, SW, SE, CAN, FR, DE, AU, UK |

### FACT_SALES

**Grain:** One row per order line item (ORDER_NUMBER + ORDER_LINE_ITEM)

| Column | Type | Description |
|---|---|---|
| ORDER_NUMBER | VARCHAR(20) DD | Degenerate dimension |
| ORDER_LINE_ITEM | NUMBER DD | Line item within order |
| ORDER_DATE_KEY | DATE FK | → DIM_DATE.DATE_KEY |
| PRODUCT_KEY | NUMBER FK | → DIM_PRODUCT.PRODUCT_KEY |
| CUSTOMER_KEY | NUMBER FK | → DIM_CUSTOMER.CUSTOMER_KEY |
| TERRITORY_KEY | NUMBER FK | → DIM_TERRITORY.TERRITORY_KEY |
| ORDER_QUANTITY | NUMBER | Units ordered |
| UNIT_PRICE | NUMBER(12,4) | List price at time of order (from DIM_PRODUCT) |
| UNIT_COST | NUMBER(12,4) | Standard cost (from DIM_PRODUCT) |
| GROSS_REVENUE | NUMBER(14,2) | ORDER_QUANTITY × UNIT_PRICE |
| TOTAL_COST | NUMBER(14,2) | ORDER_QUANTITY × UNIT_COST |
| GROSS_PROFIT | NUMBER(14,2) | GROSS_REVENUE − TOTAL_COST |
| MARGIN_PCT | NUMBER(7,2) | From DIM_PRODUCT (list margin) |
| LEAD_TIME_DAYS | NUMBER | STOCK_DATE → ORDER_DATE gap |

### FACT_RETURNS

**Grain:** One row per return record (RETURN_DATE × PRODUCT_KEY × TERRITORY_KEY)

| Column | Type | Description |
|---|---|---|
| RETURN_DATE_KEY | DATE FK | → DIM_DATE.DATE_KEY |
| PRODUCT_KEY | NUMBER FK | → DIM_PRODUCT.PRODUCT_KEY |
| TERRITORY_KEY | NUMBER FK | → DIM_TERRITORY.TERRITORY_KEY |
| RETURN_QUANTITY | NUMBER | Units returned |
| UNIT_PRICE | NUMBER(12,4) | Price at time of return |
| RETURN_REVENUE_IMPACT | NUMBER(14,2) | RETURN_QUANTITY × UNIT_PRICE (negative impact) |

---

## Analytical Views

| View | Description |
|---|---|
| VW_SALES_DETAIL | Fully joined fact + all dimensions — one row per order line |
| VW_MONTHLY_KPI | Monthly revenue, profit, orders, units, avg order value |
| VW_PRODUCT_PERFORMANCE | Revenue, profit, units sold, return rate per product |
| VW_CUSTOMER_360 | Demographics + RFM signals (Champions/Loyal/At Risk/Lost) |
| VW_TERRITORY_SUMMARY | Revenue and order share by Continent→Country→Region |
| VW_RETURN_ANALYSIS | Returns with product and territory context |
| MV_MONTHLY_REVENUE | Materialized view — pre-aggregated monthly revenue |

---

## Business Rules & Transformation Logic

| Rule | Description |
|---|---|
| Color/Size/Style cleanup | Source values of '0' → 'Unknown' / 'N/A' |
| Income bands | <40K=Low, 40-80K=Medium, 80-120K=High, ≥120K=Very High |
| Price tiers | <$50=Budget, $50-$250=Mid-Range, $250-$1000=Premium, >$1000=Luxury |
| Fiscal year | Starts July 1 — Jul-Aug-Sep = FQ1, Oct-Nov-Dec = FQ2 |
| RFM segmentation | Recency≤30d & Freq≥5=Champions; see VW_CUSTOMER_360 |
| Lead time | DATEDIFF(day, STOCK_DATE, ORDER_DATE) — can be negative |
| Sales consolidation | 2020+2021+2022 UNION ALL with SALES_YEAR column |
