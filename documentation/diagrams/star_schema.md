# Star Schema Diagram — Gold Layer
## Milestone 4: Gold Layer Star Schema

```mermaid
erDiagram

    FACT_SALES {
        int     SALES_KEY           PK
        int     CUSTOMER_KEY        FK
        int     PRODUCT_KEY         FK
        int     TERRITORY_KEY       FK
        int     CALENDAR_KEY        FK
        string  ORDER_NUMBER
        int     ORDER_LINE_ITEM
        date    ORDER_DATE
        int     ORDER_QUANTITY
        float   UNIT_PRICE
        float   UNIT_COST
        float   GROSS_REVENUE
        float   TOTAL_COST
        float   GROSS_PROFIT
        float   PROFIT_MARGIN_PCT
        date    LOAD_TIMESTAMP
    }

    FACT_RETURNS {
        int     RETURN_KEY          PK
        int     PRODUCT_KEY         FK
        int     TERRITORY_KEY       FK
        int     CALENDAR_KEY        FK
        date    RETURN_DATE
        int     RETURN_QUANTITY
        date    LOAD_TIMESTAMP
    }

    DIM_CUSTOMER {
        int     CUSTOMER_KEY        PK
        string  FULL_NAME
        string  GENDER
        date    BIRTH_DATE
        string  MARITAL_STATUS
        string  EMAIL_ADDRESS
        float   ANNUAL_INCOME
        string  INCOME_BAND
        string  OCCUPATION
        string  EDUCATION_LEVEL
        int     TOTAL_CHILDREN
        string  HOME_OWNER
    }

    DIM_PRODUCT {
        int     PRODUCT_KEY         PK
        int     SUBCATEGORY_KEY     FK
        string  PRODUCT_SKU
        string  PRODUCT_NAME
        string  MODEL_NAME
        string  PRODUCT_COLOR
        string  PRODUCT_STYLE
        float   PRODUCT_COST
        float   PRODUCT_PRICE
        string  PRICE_TIER
    }

    DIM_PRODUCT_CATEGORY {
        int     CATEGORY_KEY        PK
        string  CATEGORY_NAME
    }

    DIM_PRODUCT_SUBCATEGORY {
        int     SUBCATEGORY_KEY     PK
        int     CATEGORY_KEY        FK
        string  SUBCATEGORY_NAME
    }

    DIM_CALENDAR {
        int     CALENDAR_KEY        PK
        date    FULL_DATE
        int     DAY_OF_WEEK
        string  DAY_NAME
        int     DAY_OF_MONTH
        int     WEEK_OF_YEAR
        int     MONTH_NUMBER
        string  MONTH_NAME
        string  MONTH_SHORT
        int     QUARTER
        int     YEAR
        string  FISCAL_YEAR
        int     FISCAL_QUARTER
    }

    DIM_TERRITORY {
        int     TERRITORY_KEY       PK
        string  REGION
        string  COUNTRY
        string  CONTINENT
    }

    FACT_SALES     }o--|| DIM_CUSTOMER              : "CUSTOMER_KEY"
    FACT_SALES     }o--|| DIM_PRODUCT               : "PRODUCT_KEY"
    FACT_SALES     }o--|| DIM_TERRITORY             : "TERRITORY_KEY"
    FACT_SALES     }o--|| DIM_CALENDAR              : "CALENDAR_KEY"
    FACT_RETURNS   }o--|| DIM_PRODUCT               : "PRODUCT_KEY"
    FACT_RETURNS   }o--|| DIM_TERRITORY             : "TERRITORY_KEY"
    FACT_RETURNS   }o--|| DIM_CALENDAR              : "CALENDAR_KEY"
    DIM_PRODUCT    }o--|| DIM_PRODUCT_SUBCATEGORY   : "SUBCATEGORY_KEY"
    DIM_PRODUCT_SUBCATEGORY }o--|| DIM_PRODUCT_CATEGORY : "CATEGORY_KEY"
```

---

## Star Schema Overview

```
                    DIM_CALENDAR
                        |
DIM_CUSTOMER ——— FACT_SALES ——— DIM_TERRITORY
                        |
                    DIM_PRODUCT ——— DIM_PRODUCT_SUBCATEGORY ——— DIM_PRODUCT_CATEGORY

                    DIM_CALENDAR
                        |
         ——————————— FACT_RETURNS ——— DIM_TERRITORY
                        |
                    DIM_PRODUCT
```

---

## Grain Definitions

| Fact Table | Grain | Rows (approx) |
|-----------|-------|---------------|
| FACT_SALES | One row per order line item | ~56,000 |
| FACT_RETURNS | One row per product return | ~1,800 |

---

## Surrogate Key Strategy

All dimension tables use an integer surrogate key (`_KEY`) as the primary key.
Natural source keys are retained as separate columns for traceability.

| Dimension | Surrogate Key | Natural Key |
|-----------|--------------|-------------|
| DIM_CUSTOMER | CUSTOMER_KEY | (same as source) |
| DIM_PRODUCT | PRODUCT_KEY | PRODUCT_SKU |
| DIM_PRODUCT_SUBCATEGORY | SUBCATEGORY_KEY | (same as source) |
| DIM_PRODUCT_CATEGORY | CATEGORY_KEY | (same as source) |
| DIM_CALENDAR | CALENDAR_KEY | FULL_DATE |
| DIM_TERRITORY | TERRITORY_KEY | REGION + COUNTRY |

---

## Calculated Columns in FACT_SALES

| Column | Formula |
|--------|---------|
| GROSS_REVENUE | ORDER_QUANTITY × UNIT_PRICE |
| TOTAL_COST | ORDER_QUANTITY × UNIT_COST |
| GROSS_PROFIT | GROSS_REVENUE − TOTAL_COST |
| PROFIT_MARGIN_PCT | (GROSS_PROFIT / GROSS_REVENUE) × 100 |
