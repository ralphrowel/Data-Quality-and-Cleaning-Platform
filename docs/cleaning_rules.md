# Cleaning Rules & Transformation Reference

This document provides a detailed technical reference for all cleaning transformations supported by the **Data Quality Engine** (`src/cleaner.py`).

Transformations are deterministic, configurable, and execute in a strict sequential order to ensure consistent results.

---

## Transformation Pipeline Order

```text
 1. normalize_whitespace
 2. normalize_column_names
 3. standardize_casing
 4. map_categorical_values
 5. normalize_dates
 6. enforce_ranges
 7. impute_missing_values
 8. remove_duplicates
 9. handle_outliers
10. safe_csv_export
11. parquet_version_persistence
```

---

## 1. Normalize Whitespace (`normalize_whitespace`)

- **Description:** Trims leading and trailing whitespace from string columns and collapses multiple consecutive spaces into a single space.
- **Parameters:**
  - `columns` *(list[str] | None)*: Specific columns to clean, or `None` for all string/object columns.
- **Behavior:**
  - Converts `"   John   Doe  "` &rarr; `"John Doe"`.
  - Non-string values and `NaN` are preserved without error.

---

## 2. Normalize Column Names (`normalize_column_names`)

- **Description:** Converts column headers into standardized, database-safe `snake_case` identifiers.
- **Parameters:**
  - `case` *(str)*: Target casing style (default: `"snake"`).
- **Behavior:**
  - Replaces spaces, hyphens, and non-alphanumeric characters with underscores (`_`).
  - Converts all characters to lowercase.
  - Strips leading and trailing underscores and collapses consecutive underscores.
  - Example: `" Customer ID # "` &rarr; `"customer_id"`.

---

## 3. Standardize Casing (`standardize_casing`)

- **Description:** Standardizes text capitalization for specified columns.
- **Parameters:**
  - `casing_rules` *(dict[str, str])*: Mapping of column names to target casing (`"lower"`, `"upper"`, `"title"`, or `"capitalize"`).
- **Behavior:**
  - `"lower"`: `"USA"` &rarr; `"usa"`.
  - `"upper"`: `"usa"` &rarr; `"USA"`.
  - `"title"`: `"new york"` &rarr; `"New York"`.
  - `NaN` values remain unchanged.

---

## 4. Map Categorical Values (`map_categorical_values`)

- **Description:** Replaces known synonyms, abbreviations, typos, or category representations with canonical values.
- **Parameters:**
  - `mappings` *(dict[str, dict[Any, Any]])*: Nested dictionary mapping column names to substitution dictionaries.
- **Behavior:**
  - Example: `{"status": {"P": "Pending", "A": "Approved", "pend": "Pending"}}`
  - Values not present in the mapping dictionary are untouched.

---

## 5. Normalize Dates (`normalize_dates`)

- **Description:** Parses irregular date strings and converts them to standard ISO-8601 (`YYYY-MM-DD`).
- **Parameters:**
  - `columns` *(list[str])*: Columns containing dates.
  - `output_format` *(str)*: Target format string (default: `"%Y-%m-%d"`).
  - `dayfirst` *(bool)*: Whether to interpret ambiguous dates like `01/02/2024` as February 1st (`True`) or January 2nd (`False`).
- **Behavior:**
  - Handles mixed formats in the same column (e.g., `"2024-01-15"`, `"15/01/2024"`, `"Jan 15, 2024"`).
  - Unparseable or impossible dates (e.g., `"2024-02-31"`) become `NaT` (null) without raising fatal exceptions.

---

## 6. Numerical Range Enforcement (`enforce_ranges`)

- **Description:** Enforces domain minimum and maximum bounds on numeric columns.
- **Parameters:**
  - `range_rules` *(dict[str, dict[str, float | str]])*: Mapping of column names to range constraints:
    ```json
    {
      "age": {"min": 0, "max": 120, "strategy": "clamp"}
    }
    ```
  - `strategy` options:
    - `"clamp"`: Values below `min` are set to `min`; values above `max` are set to `max`.
    - `"nullify"`: Out-of-bounds values are converted to `NaN`.

---

## 7. Missing Value Imputation (`impute_missing_values`)

- **Description:** Replaces missing (`NaN`, `None`, empty string) values using statistical or static strategies.
- **Parameters:**
  - `imputation_rules` *(dict[str, dict[str, Any]])*: Mapping of column names to imputation strategies:
    ```json
    {
      "salary": {"strategy": "median"},
      "department": {"strategy": "mode"},
      "tax_rate": {"strategy": "constant", "fill_value": 0.0}
    }
    ```
- **Strategies:**
  - `"mean"`: Numeric mean of non-null values.
  - `"median"`: Numeric median (robust to extreme outliers).
  - `"mode"`: Most frequent value.
  - `"constant"`: Provided `fill_value` (e.g., `"Unknown"`, `0`).

---

## 8. Duplicate Row Removal (`remove_duplicates`)

- **Description:** Removes redundant duplicate rows from the dataset.
- **Parameters:**
  - `subset` *(list[str] | None)*: Subset of columns to consider when evaluating duplicates. If `None`, checks all columns.
  - `keep` *(str)*: Which duplicate to retain: `"first"`, `"last"`, or `False` (drop all duplicates). Default is `"first"`.
- **Behavior:**
  - Rows considered duplicates are dropped, and index is reset.
  - The number of purged rows is recorded in the job audit log.

---

## 9. Outlier Handling (`handle_outliers`)

- **Description:** Identifies numerical outliers using Tukey’s Interquartile Range (IQR) method and either clips them or sets them to null.
- **Formulas:**
  $$\text{IQR} = Q_3 - Q_1$$
  $$\text{Lower Bound} = Q_1 - 1.5 \times \text{IQR}$$
  $$\text{Upper Bound} = Q_3 + 1.5 \times \text{IQR}$$
- **Parameters:**
  - `outlier_rules` *(dict[str, dict[str, str]])*:
    ```json
    {
      "transaction_amount": {"strategy": "clip"}
    }
    ```
  - `strategy` options:
    - `"clip"`: Values below the lower bound become lower bound; values above become upper bound.
    - `"nullify"`: Outlier values become `NaN`.

---

## 10. Safe CSV Export Sanitization (`safe_csv_export`)

- **Description:** Sanitizes all string values prior to exporting to CSV to neutralize **CSV Formula Injection (CWE-1236)**.
- **Trigger Characters:**
  - `=` (Formula initiator)
  - `+` (Arithmetic formula initiator)
  - `-` (Arithmetic formula initiator)
  - `@` (Function caller)
  - `\t` (Tab character used for field breaking)
  - `\r` (Carriage return used for command injection)
- **Sanitization Rule:**
  - Any cell starting with any of the trigger characters is prefixed with a single quotation mark (`'`).
  - Example: `=CMD('calc')` &rarr; `'=CMD('calc')`.

---

## 11. Parquet Snapshot Persistence (`parquet_version_persistence`)

- **Description:** Saves every dataset version to immutable Apache Parquet files.
- **Compression:** Snappy compression.
- **Type Preservation:**
  - Preserves native Arrow and Pandas datatypes (`int64`, `float64`, `datetime64[ns]`, `category`).
  - Avoids string/float precision degradation inherent to intermediate CSV roundtrips.
