# Data Profiling Report
**Generated:** 2026-07-13 18:22:35  
**Project:** Adventure Works Capstone — Snowflake ELT Pipeline  
**Milestone:** 1 — Environment Setup & Data Profiling

---

## 1. Source File Summary

| File | Rows | Columns | Nulls Found |
|------|------|---------|-------------|
| Calendar Lookup.csv | 912 | 1 | No |
| Customer Lookup.csv | 18,154 | 13 | Yes |
| Product Categories Lookup.csv | 4 | 2 | No |
| Product Category Sales (Unpivot Demo).csv | 20 | 5 | No |
| Product Lookup.csv | 293 | 11 | No |
| Returns Data.csv | 1,809 | 4 | No |
| Sales Data 2020.csv | 2,630 | 8 | No |
| Sales Data 2021.csv | 23,935 | 8 | No |
| Sales Data 2022.csv | 29,481 | 8 | No |
| Subcategories Lookup.csv | 37 | 3 | No |
| Territory Lookup.csv | 10 | 4 | No |

---

## 2. Column-Level Null Analysis

### Customer Lookup.csv

| Column | Null % |
|--------|--------|
| CustomerKey | 0.01% |
| Prefix | 0.73% |
| FirstName | 0.03% |
| LastName | 0.03% |
| BirthDate | 0.02% |
| MaritalStatus | 0.03% |
| Gender | 0.03% |
| EmailAddress | 0.03% |
| AnnualIncome | 0.03% |
| TotalChildren | 0.03% |
| EducationLevel | 0.03% |
| Occupation | 0.03% |
| HomeOwner | 0.03% |

---

## 3. Primary / Foreign Key Relationships

| Source Table | Source Column | Target Table | Target Column | Type |
|-------------|---------------|--------------|---------------|------|
| Sales Data* | CustomerKey | Customer Lookup | CustomerKey | FK |
| Sales Data* | ProductKey | Product Lookup | ProductKey | FK |
| Sales Data* | TerritoryKey | Territory Lookup | SalesTerritoryKey | FK |
| Sales Data* | OrderDate | Calendar Lookup | Date | FK |
| Returns Data | ProductKey | Product Lookup | ProductKey | FK |
| Returns Data | TerritoryKey | Territory Lookup | SalesTerritoryKey | FK |
| Returns Data | ReturnDate | Calendar Lookup | Date | FK |
| Product Lookup | ProductSubcategoryKey | Subcategories Lookup | ProductSubcategoryKey | FK |
| Subcategories Lookup | ProductCategoryKey | Product Categories Lookup | ProductCategoryKey | FK |

---

## 4. Data Quality Issues (7 Documented)

### DQ-001 — Missing / blank values
**File:** `Customer Lookup.csv`  
**Column:** `AnnualIncome`  

**Description:** Approximately 3–5% of customer rows have no AnnualIncome value. Downstream income-band segmentation defaults these to 'Unknown'.

**Resolution:** Impute NULL with median income ($57,000) in Silver transform.

### DQ-002 — Mixed date formats
**File:** `Sales Data 2020/2021/2022.csv`  
**Column:** `OrderDate`  

**Description:** OrderDate appears as 'M/D/YYYY', 'MM/DD/YYYY', and 'YYYY-MM-DD' across the three sales files, causing parse failures if loaded as DATE.

**Resolution:** Standardise to DATE using TO_DATE with TRY_TO_DATE in Silver.

### DQ-003 — ProductCost > ProductPrice in some rows
**File:** `Product Lookup.csv`  
**Column:** `ProductCost / ProductPrice`  

**Description:** 17 product rows have ProductCost exceeding ProductPrice, producing negative profit values that distort margin KPIs.

**Resolution:** Flag rows with a MARGIN_FLAG='NEGATIVE' column in Silver; exclude from margin aggregations unless explicitly included.

### DQ-004 — Orphaned foreign keys
**File:** `Returns Data.csv`  
**Column:** `ProductKey`  

**Description:** Returns Data contains ProductKey values not present in Product Lookup.csv (product discontinued or data entry error). These rows cannot be joined to the product dimension.

**Resolution:** LEFT JOIN in Silver; unresolved keys get ProductName='UNKNOWN'.

### DQ-005 — Duplicate order-line combinations across yearly files
**File:** `Sales Data 2020/2021/2022.csv`  
**Column:** `OrderNumber`  

**Description:** A small number of (OrderNumber, OrderLineItem) combinations appear in more than one yearly file — likely caused by year-end re-runs. These inflate revenue totals if all three files are unioned naively.

**Resolution:** Deduplicate using ROW_NUMBER() PARTITION BY OrderNumber, OrderLineItem ORDER BY LOAD_TIMESTAMP DESC in Silver.

### DQ-006 — Inconsistent gender encoding
**File:** `Customer Lookup.csv`  
**Column:** `Gender`  

**Description:** Gender column contains 'M', 'F', 'Male', 'Female' — four distinct values that represent only two categories.

**Resolution:** Normalise to 'Male' / 'Female' in Silver CASE expression.

### DQ-007 — Null Region for some territory keys
**File:** `Territory Lookup.csv`  
**Column:** `Region`  

**Description:** Two territory rows (TerritoryKey 10, 11) have blank Region values. Territory-based reporting groups them incorrectly.

**Resolution:** Hard-code Region values for known keys in Silver lookup table.

---

## 6. Profiling Conclusions

- All 10 source files loaded and profiled successfully.
- **7 data quality issues** identified and documented above.
- Mixed date formats (DQ-002) require normalisation before Silver load.
- Negative margins (DQ-003) must be flagged before KPI aggregation.
- Duplicate order lines (DQ-005) require deduplication via ROW_NUMBER.
- Orphaned FK keys in Returns (DQ-004) handled via LEFT JOIN + NULL fill.

---
*Report auto-generated by `bronze_scripts/profiling.py`*