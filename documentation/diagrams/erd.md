# Entity Relationship Diagram (ERD)
## Source CSV Files — Primary & Foreign Key Relationships

```mermaid
erDiagram

    SALES_DATA {
        int     OrderNumber         PK
        int     OrderLineItem       PK
        date    OrderDate
        int     CustomerKey         FK
        int     ProductKey          FK
        int     TerritoryKey        FK
        int     OrderQuantity
    }

    RETURNS_DATA {
        date    ReturnDate
        int     ProductKey          FK
        int     TerritoryKey        FK
        int     ReturnQuantity
    }

    CUSTOMER_LOOKUP {
        int     CustomerKey         PK
        string  Prefix
        string  FirstName
        string  LastName
        date    BirthDate
        string  MaritalStatus
        string  Gender
        string  EmailAddress
        float   AnnualIncome
        int     TotalChildren
        string  EducationLevel
        string  Occupation
        string  HomeOwner
    }

    PRODUCT_LOOKUP {
        int     ProductKey          PK
        string  ProductSubcategoryKey FK
        string  ProductSKU
        string  ProductName
        string  ModelName
        string  ProductDescription
        string  ProductColor
        float   ProductSize
        string  ProductStyle
        float   ProductCost
        float   ProductPrice
    }

    PRODUCT_CATEGORIES_LOOKUP {
        int     ProductCategoryKey  PK
        string  CategoryName
    }

    SUBCATEGORIES_LOOKUP {
        int     ProductSubcategoryKey PK
        int     ProductCategoryKey    FK
        string  SubcategoryName
    }

    CALENDAR_LOOKUP {
        date    Date                PK
        int     DayOfWeek
        string  DayName
        int     DayOfMonth
        int     DayOfYear
        int     WeekOfYear
        int     Month
        string  MonthName
        int     Quarter
        int     Year
    }

    TERRITORY_LOOKUP {
        int     SalesTerritoryKey   PK
        string  Region
        string  Country
        string  Continent
    }

    SALES_DATA         }o--|| CUSTOMER_LOOKUP         : "CustomerKey"
    SALES_DATA         }o--|| PRODUCT_LOOKUP          : "ProductKey"
    SALES_DATA         }o--|| TERRITORY_LOOKUP        : "TerritoryKey"
    SALES_DATA         }o--|| CALENDAR_LOOKUP         : "OrderDate = Date"
    RETURNS_DATA       }o--|| PRODUCT_LOOKUP          : "ProductKey"
    RETURNS_DATA       }o--|| TERRITORY_LOOKUP        : "TerritoryKey"
    RETURNS_DATA       }o--|| CALENDAR_LOOKUP         : "ReturnDate = Date"
    PRODUCT_LOOKUP     }o--|| SUBCATEGORIES_LOOKUP    : "ProductSubcategoryKey"
    SUBCATEGORIES_LOOKUP }o--|| PRODUCT_CATEGORIES_LOOKUP : "ProductCategoryKey"
```

---

## Key Relationships Summary

| Source Table | Column | References | Column |
|-------------|--------|-----------|--------|
| Sales Data (2020–2022) | CustomerKey | Customer Lookup | CustomerKey |
| Sales Data (2020–2022) | ProductKey | Product Lookup | ProductKey |
| Sales Data (2020–2022) | TerritoryKey | Territory Lookup | SalesTerritoryKey |
| Sales Data (2020–2022) | OrderDate | Calendar Lookup | Date |
| Returns Data | ProductKey | Product Lookup | ProductKey |
| Returns Data | TerritoryKey | Territory Lookup | SalesTerritoryKey |
| Returns Data | ReturnDate | Calendar Lookup | Date |
| Product Lookup | ProductSubcategoryKey | Subcategories Lookup | ProductSubcategoryKey |
| Subcategories Lookup | ProductCategoryKey | Product Categories Lookup | ProductCategoryKey |

---

## Cardinality Notes

- `SALES_DATA` → `CUSTOMER_LOOKUP`: Many-to-one (one customer, many orders)
- `SALES_DATA` → `PRODUCT_LOOKUP`: Many-to-one (one product, many order lines)
- `RETURNS_DATA` → `PRODUCT_LOOKUP`: Many-to-one (one product, many returns)
- `PRODUCT_LOOKUP` → `SUBCATEGORIES_LOOKUP` → `PRODUCT_CATEGORIES_LOOKUP`: Many-to-one-to-one (category hierarchy)
