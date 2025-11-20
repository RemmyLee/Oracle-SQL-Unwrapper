# Oracle APEX Compatibility Guide

**Version:** 1.0
**Last Updated:** 2025-11-20

---

## Overview

PL/SQL Workbench provides **full compatibility with Oracle Application Express (APEX)** dashboards, allowing you to:

1. **Import APEX dashboards** - Export from APEX and import into PL/SQL Workbench
2. **Export to APEX format** - Create dashboards in PL/SQL Workbench and export to APEX
3. **Automatic SQL conversion** - APEX-specific table references automatically converted to standard Oracle
4. **Component mapping** - APEX regions/items mapped to dashboard components

This enables seamless migration between APEX and PL/SQL Workbench, or using both systems in parallel.

---

## Table of Contents

1. [Why APEX Compatibility?](#why-apex-compatibility)
2. [Supported APEX Features](#supported-apex-features)
3. [APEX Table Mappings](#apex-table-mappings)
4. [Importing APEX Dashboards](#importing-apex-dashboards)
5. [Exporting to APEX](#exporting-to-apex)
6. [SQL Conversion](#sql-conversion)
7. [Component Mapping](#component-mapping)
8. [Limitations & Workarounds](#limitations--workarounds)
9. [Examples](#examples)
10. [API Reference](#api-reference)

---

## Why APEX Compatibility?

### Use Cases

**1. APEX Migration**
- Migrate existing APEX applications to PL/SQL Workbench
- Reduce APEX licensing costs
- Modernize legacy APEX dashboards

**2. Hybrid Deployment**
- Use APEX for forms/data entry
- Use PL/SQL Workbench for dashboards/analytics
- Share dashboard definitions between systems

**3. APEX Development**
- Prototype dashboards in PL/SQL Workbench (faster)
- Export to APEX for production deployment
- Leverage APEX's enterprise features

**4. Multi-Environment**
- Development in PL/SQL Workbench (local)
- Production in APEX (cloud)
- Consistent dashboard definitions

---

## Supported APEX Features

### ✅ Fully Supported

| APEX Feature | PL/SQL Workbench Equivalent |
|--------------|----------------------------|
| Classic Reports | Table components |
| Interactive Reports | Table components with search/filter |
| Interactive Grids | Table components with inline editing |
| Charts (all types) | Chart components (pie, bar, line, area, scatter) |
| Static Content | Text components (HTML/Markdown) |
| Page Items (filters) | Filter components |
| SQL queries | SQL data sources |
| Regions | Dashboard components |
| Page layout | Grid layout system |

### ⚠️ Partially Supported

| APEX Feature | Status | Notes |
|--------------|--------|-------|
| PL/SQL Processes | Limited | Non-rendering processes ignored |
| Dynamic Actions | Not supported | Convert to static components |
| Plugins | Limited | Custom components may need rewrite |
| APEX Functions | Converted | See SQL conversion section |
| Session State | Converted | Mapped to parameters |

### ❌ Not Supported

| APEX Feature | Reason | Workaround |
|--------------|--------|------------|
| Application Logic | Different architecture | Use backend services |
| Authentication | Uses own auth system | Map users manually |
| Authorization Schemes | Uses RBAC | Configure roles |
| Breadcrumbs | UI element | Implement in frontend |
| Navigation | Different structure | Create custom navigation |

---

## APEX Table Mappings

APEX uses special views for application metadata. These are automatically converted to standard Oracle views.

### Application Views

| APEX View | Converts To | Purpose |
|-----------|-------------|---------|
| `APEX_APPLICATIONS` | `USER_OBJECTS` | Application list |
| `APEX_APPLICATION_PAGES` | `USER_TAB_COLUMNS` | Page definitions |
| `APEX_APPLICATION_PAGE_ITEMS` | `USER_TAB_COLUMNS` | Page item definitions |
| `APEX_APPLICATION_PAGE_REGIONS` | `USER_TABLES` | Region definitions |

### Workspace Views

| APEX View | Converts To | Purpose |
|-----------|-------------|---------|
| `APEX_WORKSPACES` | `DBA_USERS` | Workspace list |
| `APEX_WORKSPACE_SCHEMAS` | `ALL_USERS` | Available schemas |
| `APEX_WORKSPACE_USERS` | `ALL_USERS` | User list |

### Collection Views

| APEX View | Converts To | Purpose |
|-----------|-------------|---------|
| `APEX_COLLECTIONS` | `USER_TABLES` | Collections list |
| `APEX_COLLECTION_MEMBERS` | `USER_TAB_COLUMNS` | Collection data |

### Function Conversions

| APEX Function | Converts To | Notes |
|---------------|-------------|-------|
| `APEX_UTIL.GET_USERNAME` | `USER` | Current database user |
| `APEX_UTIL.GET_SESSION_STATE(:item)` | `SYS_CONTEXT(...)` | Session variables |
| `APEX_ITEM.TEXT(...)` | `NULL` | Requires manual review |
| `APEX_STRING.SPLIT(...)` | `REGEXP_SUBSTR(...)` | String splitting |
| `APEX_JSON.PARSE(...)` | `JSON_TABLE(...)` | JSON parsing |

**Note:** Some APEX functions have no direct equivalent and are converted to `NULL`. These require manual review and conversion.

---

## Importing APEX Dashboards

### Step 1: Export from APEX

**In APEX:**

1. Navigate to your APEX application
2. Go to **Shared Components** → **Export**
3. Select **Page** export
4. Choose the page(s) to export
5. Click **Export**
6. Save the `.sql` file

**Alternative - JSON Export:**

```sql
-- Run in APEX SQL Workshop
SELECT APEX_EXPORT.GET_PAGE(
    p_application_id => 100,
    p_page_id => 1
) AS json_export
FROM DUAL;
```

### Step 2: Convert SQL to JSON

APEX exports are in SQL format. Convert to JSON:

```python
# Python script to parse APEX export
import json
import re

def parse_apex_export(apex_sql):
    # Extract page definition
    # Parse regions, items, etc.
    # Convert to JSON structure
    pass
```

Or use the provided conversion utility:

```bash
python tools/apex_parser.py --input apex_page.sql --output apex_page.json
```

### Step 3: Import via API

**Using curl:**

```bash
curl -X POST http://localhost:8000/api/apex/import \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d @apex_page.json
```

**Request Body:**

```json
{
  "apex_export": {
    "page_id": 1,
    "page_name": "Sales Dashboard",
    "page_group": "Analytics",
    "regions": [
      {
        "name": "Sales by Region",
        "type": "CHART",
        "chart_type": "BAR",
        "source_type": "SQL",
        "source": "SELECT region, SUM(sales) as total FROM sales_data GROUP BY region",
        "label_column": "REGION",
        "value_column": "TOTAL"
      },
      {
        "name": "Recent Orders",
        "type": "INTERACTIVE_REPORT",
        "source_type": "SQL",
        "source": "SELECT order_id, customer, amount, order_date FROM orders ORDER BY order_date DESC"
      }
    ],
    "items": [
      {
        "name": "P1_REGION",
        "type": "SELECT_LIST",
        "label": "Filter by Region",
        "lov_definition": "SELECT region_name, region_id FROM regions"
      }
    ]
  },
  "options": {
    "auto_convert_queries": true,
    "create_data_sources": true,
    "import_as_draft": false
  }
}
```

**Response:**

```json
{
  "success": true,
  "dashboard": {
    "id": 123,
    "title": "Sales Dashboard",
    "slug": "sales-dashboard",
    "components": [...],
    "data_sources": [...]
  },
  "conversion_warnings": [
    "Converted APEX_APPLICATIONS to USER_OBJECTS",
    "Found APEX bind variable :P1_REGION - mapped to parameter"
  ],
  "message": "APEX dashboard imported successfully"
}
```

### Step 4: Review and Adjust

1. Open imported dashboard in PL/SQL Workbench
2. Review **conversion warnings**
3. Test all components
4. Adjust SQL queries if needed
5. Configure data source connections
6. Publish dashboard

---

## Exporting to APEX

### Step 1: Export from PL/SQL Workbench

**Using API:**

```bash
curl -X GET "http://localhost:8000/api/apex/export/123?app_id=100&page_id=50" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -o apex_export.json
```

**Query Parameters:**
- `app_id` - APEX application ID (default: 100)
- `page_id` - APEX page ID (default: dashboard_id + 1000)

**Response:**

```json
{
  "success": true,
  "apex_export": {
    "application_id": 100,
    "page_id": 50,
    "page_name": "Sales Dashboard",
    "page_title": "Sales Dashboard",
    "page_group": "Dashboards",
    "regions": [
      {
        "name": "Sales by Region",
        "type": "CHART",
        "chart_type": "BAR",
        "source_type": "SQL",
        "source": "SELECT region, SUM(sales) as total FROM sales_data GROUP BY region"
      }
    ]
  }
}
```

### Step 2: Import to APEX

**In APEX Application Builder:**

1. Navigate to **Create Page** → **Blank Page**
2. Use page ID from export (e.g., 50)
3. For each region in export:
   - Create region with matching type
   - Set SQL source
   - Configure chart/report settings
4. Test the page

**Automated Import (Future):**

```bash
# Generate APEX SQL import script
python tools/apex_generator.py --input apex_export.json --output apex_page.sql

# Import in APEX
# SQL Workshop → SQL Scripts → Upload → Run
```

---

## SQL Conversion

### Automatic Conversions

The system automatically converts APEX-specific SQL to standard Oracle SQL.

**Example 1: APEX Views**

```sql
-- Original APEX SQL
SELECT
    application_name,
    owner,
    version
FROM APEX_APPLICATIONS
WHERE workspace = 'PRODUCTION'

-- Converted SQL
SELECT
    object_name as application_name,
    owner,
    NULL as version
FROM USER_OBJECTS
WHERE object_type = 'APPLICATION'
```

**Example 2: APEX Functions**

```sql
-- Original APEX SQL
SELECT
    employee_id,
    first_name,
    last_name,
    department
FROM employees
WHERE department = APEX_UTIL.GET_SESSION_STATE('P1_DEPARTMENT')

-- Converted SQL
SELECT
    employee_id,
    first_name,
    last_name,
    department
FROM employees
WHERE department = :P1_DEPARTMENT  -- Mapped to parameter
```

**Example 3: APEX Session Items**

```sql
-- Original APEX SQL
SELECT * FROM orders
WHERE order_date >= TO_DATE(:P1_START_DATE, 'DD-MON-YYYY')
  AND order_date <= TO_DATE(:P1_END_DATE, 'DD-MON-YYYY')
  AND user_id = APEX_UTIL.GET_CURRENT_USER_ID()

-- Converted SQL
SELECT * FROM orders
WHERE order_date >= TO_DATE(:start_date, 'DD-MON-YYYY')
  AND order_date <= TO_DATE(:end_date, 'DD-MON-YYYY')
  AND user_id = USER
```

### Manual Conversion Tool

Convert SQL without importing:

```bash
curl -X POST http://localhost:8000/api/apex/convert-sql \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM APEX_APPLICATIONS WHERE application_id = :APP_ID"
  }'
```

**Response:**

```json
{
  "success": true,
  "original_sql": "SELECT * FROM APEX_APPLICATIONS WHERE application_id = :APP_ID",
  "converted_sql": "SELECT * FROM USER_OBJECTS WHERE object_id = :app_id",
  "warnings": [
    "Converted APEX_APPLICATIONS to USER_OBJECTS",
    "Found APEX bind variable :APP_ID - mapped to :app_id"
  ]
}
```

---

## Component Mapping

### APEX Regions → Dashboard Components

| APEX Region Type | Component Type | Configuration |
|------------------|----------------|---------------|
| Classic Report | `table` | Basic table with columns |
| Interactive Report | `table` | Searchable, filterable table |
| Interactive Grid | `table` | Editable table (if supported) |
| Chart | `chart` | Chart type auto-detected |
| Static Content | `text` | HTML/Markdown content |
| HTML Region | `text` | Raw HTML |
| Form | `filter` | Multiple filters |
| List | `table` | Simple list display |

### APEX Chart Types → Chart Types

| APEX Chart | Our Chart | Notes |
|------------|-----------|-------|
| Bar | `bar` | Vertical/horizontal bars |
| Column | `bar` | Same as bar |
| Line | `line` | Line graph |
| Area | `area` | Filled area |
| Pie | `pie` | Pie/donut chart |
| Scatter | `scatter` | Scatter plot |
| Combo | `line` | Multiple series |

### APEX Page Items → Filters

| APEX Item Type | Filter Type | Notes |
|----------------|-------------|-------|
| Select List | `dropdown` | Single/multi-select |
| Date Picker | `date_range` | Date range filter |
| Text Field | `text_search` | Free text search |
| Number Field | `number_range` | Numeric range |
| Checkbox | `multi_select` | Multiple options |

---

## Limitations & Workarounds

### Limitation 1: APEX Collections

**Issue:** APEX Collections (`APEX_COLLECTIONS`) have no direct equivalent.

**Workaround:**
- Use temporary tables
- Use session-based caching
- Store in Redis with TTL

**Example:**
```sql
-- APEX Collection
INSERT INTO APEX_COLLECTIONS (collection_name, c001, c002)
VALUES ('MY_CART', product_id, quantity);

-- Workaround: Temp table
CREATE GLOBAL TEMPORARY TABLE temp_cart (
    session_id VARCHAR2(100),
    product_id NUMBER,
    quantity NUMBER
) ON COMMIT PRESERVE ROWS;
```

### Limitation 2: APEX Session State

**Issue:** `APEX_UTIL.SET_SESSION_STATE()` doesn't work outside APEX.

**Workaround:**
- Use dashboard parameters
- Pass via query parameters
- Store in component config

### Limitation 3: APEX Dynamic Actions

**Issue:** JavaScript-based dynamic actions can't be imported.

**Workaround:**
- Implement in frontend JavaScript
- Use dashboard events system
- Convert to static components

### Limitation 4: APEX Plugins

**Issue:** Custom APEX plugins have no equivalent.

**Workaround:**
- Rewrite as custom components
- Use similar built-in components
- Implement in frontend

### Limitation 5: APEX Authorization

**Issue:** APEX authorization schemes are application-specific.

**Workaround:**
- Map to PL/SQL Workbench roles
- Configure dashboard sharing
- Use access levels (private/team/org/public)

---

## Examples

### Example 1: Simple Report Dashboard

**APEX Export:**

```json
{
  "page_id": 10,
  "page_name": "Employee Report",
  "regions": [
    {
      "name": "Employees",
      "type": "INTERACTIVE_REPORT",
      "source_type": "SQL",
      "source": "SELECT employee_id, first_name, last_name, email, department FROM employees ORDER BY last_name"
    }
  ]
}
```

**Import:**

```bash
curl -X POST http://localhost:8000/api/apex/import \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "apex_export": {...},
    "options": {"create_data_sources": true}
  }'
```

**Result:** Table component with employee data.

### Example 2: Chart Dashboard with Filter

**APEX Export:**

```json
{
  "page_id": 20,
  "page_name": "Sales Dashboard",
  "regions": [
    {
      "name": "Sales by Region",
      "type": "CHART",
      "chart_type": "BAR",
      "source": "SELECT region, SUM(amount) as total FROM sales WHERE year = :P20_YEAR GROUP BY region",
      "label_column": "REGION",
      "value_column": "TOTAL"
    }
  ],
  "items": [
    {
      "name": "P20_YEAR",
      "type": "SELECT_LIST",
      "label": "Year",
      "lov_definition": "SELECT DISTINCT year, year FROM sales ORDER BY year DESC"
    }
  ]
}
```

**Import:** Creates dashboard with bar chart and year filter.

### Example 3: Multi-Region Dashboard

**APEX Export:**

```json
{
  "page_id": 30,
  "page_name": "Executive Dashboard",
  "regions": [
    {
      "name": "Revenue",
      "type": "STATIC_CONTENT",
      "source": "<h2>$${total_revenue}</h2>"
    },
    {
      "name": "Monthly Trend",
      "type": "CHART",
      "chart_type": "LINE",
      "source": "SELECT month, revenue FROM monthly_revenue ORDER BY month_num"
    },
    {
      "name": "Top Products",
      "type": "INTERACTIVE_REPORT",
      "source": "SELECT product_name, units_sold, revenue FROM product_sales ORDER BY revenue DESC FETCH FIRST 10 ROWS ONLY"
    }
  ]
}
```

**Import:** Creates 3 components (metric, line chart, table).

---

## API Reference

### Import APEX Dashboard

```
POST /api/apex/import
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "apex_export": { ... },
  "options": {
    "auto_convert_queries": true,
    "create_data_sources": true,
    "import_as_draft": true
  }
}
```

**Response:**
```json
{
  "success": true,
  "dashboard": { ... },
  "conversion_warnings": [ ... ]
}
```

**Rate Limit:** 10 per minute

### Export to APEX

```
GET /api/apex/export/<dashboard_id>?app_id=100&page_id=50
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "apex_export": { ... }
}
```

**Rate Limit:** 20 per minute

### Convert SQL

```
POST /api/apex/convert-sql
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "sql": "SELECT * FROM APEX_APPLICATIONS"
}
```

**Response:**
```json
{
  "success": true,
  "original_sql": "...",
  "converted_sql": "...",
  "warnings": [ ... ]
}
```

**Rate Limit:** 30 per minute

### Validate Export

```
POST /api/apex/validate
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "apex_export": { ... }
}
```

**Response:**
```json
{
  "success": true,
  "valid": true,
  "issues": [],
  "warnings": [],
  "component_count": 5,
  "data_source_count": 3
}
```

**Rate Limit:** 20 per minute

### Preview Import

```
POST /api/apex/preview
Authorization: Bearer <token>
Content-Type: application/json
```

**Request:**
```json
{
  "apex_export": { ... }
}
```

**Response:**
```json
{
  "success": true,
  "preview": {
    "title": "Dashboard Name",
    "component_count": 5,
    "components": [...],
    "warnings": [...]
  }
}
```

**Rate Limit:** 10 per minute

### Get Table Mappings

```
GET /api/apex/table-mappings
```

**Response:**
```json
{
  "success": true,
  "mappings": {
    "APEX_APPLICATIONS": "USER_OBJECTS",
    ...
  },
  "function_mappings": {
    "APEX_UTIL.GET_USERNAME": "USER",
    ...
  }
}
```

**Rate Limit:** 100 per minute

---

## Best Practices

### 1. Test Conversions

Always preview and validate before importing:

```bash
# Preview first
curl -X POST http://localhost:8000/api/apex/preview -d @export.json

# Validate
curl -X POST http://localhost:8000/api/apex/validate -d @export.json

# Then import
curl -X POST http://localhost:8000/api/apex/import -d @export.json
```

### 2. Review SQL Conversions

Check all SQL queries after import:

1. Review conversion warnings
2. Test queries in SQL editor
3. Verify parameter mappings
4. Check data source connections

### 3. Incremental Migration

Don't migrate everything at once:

1. Start with simple dashboards
2. Test thoroughly
3. Gradually migrate complex dashboards
4. Keep APEX as fallback initially

### 4. Maintain Documentation

Document your conversions:

- Which APEX pages map to which dashboards
- Custom SQL conversions performed
- Known limitations or workarounds
- User mapping between systems

### 5. Version Control

Keep exports in version control:

```bash
git add apex_exports/
git commit -m "Export APEX page 10 - Employee Report"
```

---

## Troubleshooting

### Issue: Import Fails

**Symptoms:** 400/500 error on import

**Diagnosis:**
```bash
# Validate first
curl -X POST http://localhost:8000/api/apex/validate -d @export.json

# Check logs
tail -f logs/app.log
```

**Solutions:**
- Fix JSON structure
- Review validation issues
- Check required fields

### Issue: SQL Doesn't Work

**Symptoms:** Query errors after import

**Diagnosis:**
```bash
# Test conversion
curl -X POST http://localhost:8000/api/apex/convert-sql \
  -d '{"sql": "YOUR_APEX_SQL"}'
```

**Solutions:**
- Review conversion warnings
- Manually adjust SQL
- Map parameters correctly
- Update table references

### Issue: Missing Components

**Symptoms:** Not all regions imported

**Diagnosis:** Check conversion warnings

**Solutions:**
- Some APEX regions may not have equivalents
- Convert unsupported types manually
- Use similar component types

---

## Future Enhancements

Planned improvements to APEX compatibility:

1. **Direct APEX Integration** - Connect to APEX REST APIs
2. **Real-time Sync** - Keep dashboards in sync between systems
3. **Plugin Support** - Import custom APEX plugins
4. **Dynamic Actions** - Convert to frontend events
5. **Automated Testing** - Validate imported dashboards
6. **Batch Import** - Import multiple pages at once

---

## Support

For APEX compatibility issues:

- **GitHub Issues**: Report bugs/feature requests
- **Documentation**: This guide
- **API Docs**: `/api/docs/` (if enabled)
- **Examples**: `examples/apex/` directory

---

**Version:** 1.0
**Last Updated:** 2025-11-20
**Compatible with:** Oracle APEX 19.x, 20.x, 21.x, 22.x, 23.x
