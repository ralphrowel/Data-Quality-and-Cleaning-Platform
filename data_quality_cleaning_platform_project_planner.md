# Data Quality & Cleaning Platform — Project Planner

## Project Overview

**Project:** Data Quality & Cleaning Platform

**Goal:** Build a practical data-quality platform that answers:

> **"Can I trust this dataset before I analyze it?"**

The system will accept datasets, profile their structure and contents, detect quality problems, perform controlled cleaning operations, preserve dataset history, generate quality reports, and expose the results through a web application and Power BI.

The project is intentionally designed to be both a **learning path** and a **portfolio project**.

---

# 0. Project Vision

## Core Workflow

```text
Raw Dataset
    ↓
Data Ingestion
    ↓
Data Profiling
    ↓
Data Quality Checks
    ↓
Data Cleaning
    ↓
Clean Dataset
    ↓
Quality Report
    ↓
Analytics / Power BI
```

## Main Question

> Can the data be trusted before it is used for analysis?

## Portfolio Goals

This project should demonstrate practical ability in:

- Python
- Pandas / NumPy
- Data cleaning
- Exploratory data analysis
- Data quality concepts
- SQL
- PostgreSQL
- Data validation
- ETL concepts
- Django / Django REST Framework
- React
- REST APIs
- Testing
- Power BI
- DAX
- Data visualization
- Basic deployment

---

# 1. Project Rules

These rules apply throughout the project.

## Rule 1 — Build one step at a time

Do not jump directly into the full application.

Each phase should teach a concept before turning it into a feature.

## Rule 2 — Understand before implementing

For every major feature:

1. Understand the problem.
2. Explore a small example.
3. Decide how the system should behave.
4. Implement the smallest useful version.
5. Test it.
6. Move to the next step.

## Rule 3 — Avoid unnecessary scope

The project should remain focused on:

> **Data quality → cleaning → trustworthy data → analytics**

Features that do not support that goal should be postponed.

## Rule 4 — Preserve the original data

The raw dataset should never be silently destroyed.

The system should be able to distinguish:

```text
Raw Dataset
     ↓
Cleaned Dataset
```

and preserve the transformation history.

## Rule 5 — Priority Hierarchy (Core Engine First)

Do not let the application become bloated across 5 different engineering roles simultaneously.

```text
        ⭐⭐⭐⭐⭐
   DATA QUALITY ENGINE
          │
     ┌────┴────┐
     ↓         ↓
  Cleaning   Profiling
     │         │
     └────┬────┘
          ↓
    Quality Score
          ↓
      Power BI
          ↓
    Django / React
```

The **Data Quality Engine (V1–V5)** and **Power BI Analytics (V9)** are the primary stars of the portfolio. Django and React serve as lightweight, minimal supporting interfaces.

---

# 2. Scope

## MVP — In Scope

- CSV upload (size ≤ 25 MB)
- Excel upload (.xlsx, size ≤ 25 MB)
- In-memory synchronous processing for MVP (task workers deferred)
- Dataset profiling (row/column stats, dtypes, missing values, duplicates)
- Data validation (format, range, categorical consistency, statistical outliers)
- Deterministic data cleaning pipeline
- Cleaning logs & before/after comparison
- Data quality score & dimension breakdown (Completeness, Validity, Uniqueness, Consistency)
- Hybrid storage model:
  - **PostgreSQL**: Stores metadata, quality reports, issues, versions, and audit logs
  - **Filesystem / Object Storage**: Stores actual dataset files using **Apache Parquet** internally to preserve exact schema types
- Cleaned dataset export (CSV format with formula-injection sanitization)
- Basic user authentication and dataset ownership isolation (User A cannot access User B's datasets)
- Minimal Django REST API
- Minimal React single-page interface
- Power BI reporting on platform quality metrics & governance
- DAX measures for quality KPIs
- Automated tests (pytest)
- Basic deployment with environment variables

## Later — Out of MVP / Deferred

- Celery + Redis background task queues (deferred to scale/later phases)
- Scheduled ingestion & real-time streaming data
- Large-scale distributed processing (Spark/Dask)
- Advanced machine-learning anomaly detection
- Multiple enterprise organizations / complex team approval workflows
- Automated email notifications
- AI-powered cleaning recommendations
- Mobile application
- Advanced cloud data lake architecture

---

# 3. Technology Direction

## Data Processing & Engine

- Python 3.11+
- Pandas
- NumPy
- PyArrow (for internal Parquet dataset versioning)

## Dataset & Metadata Storage

- **PostgreSQL**: Relational storage for metadata, dataset versions, quality metrics, issue logs, and audit trails
- **Filesystem / Object Storage**: Storage for immutable dataset files (`raw.csv`, `v1.parquet`, `v2.parquet`) using UUID-based internal file paths

## Backend

- Django
- Django REST Framework (DRF)
- Synchronous request processing initially (with ≤ 25 MB upload limit; background queues deferred)

## Frontend

- React
- Vite
- Focused, clean, lightweight single-page UI

## Analytics & BI

- Power BI Desktop
- DAX
- **Scope**: Data Quality Governance & Platform Analytics (analyzing dataset quality metrics across uploads, issue frequency, resolution rates, and cleaning impact)

## Testing

- pytest

## Version Control

- Git
- GitHub

## Deployment

Deployment provider will be decided later.

The application should use environment variables from the beginning so that deployment is not tied to a specific provider.

---

# 4. PHASE 0 — Project Definition

## V0.1 — Define the Problem

Document:

- What problem does the platform solve?
- Who is the intended user?
- What datasets will it support?
- What does "clean data" mean?
- What problems should it detect?
- What problems can be automatically fixed?
- What problems should require user review?

### Deliverable

A short project specification.

---

## V0.2 — Define the MVP

Create the initial feature boundary.

### Deliverable

A checklist separating:

- MVP
- Later features
- Explicitly excluded features

---

## V0.3 — Define the Workflow

Document the expected user journey.

Example:

```text
Upload Dataset
      ↓
System Profiles Dataset
      ↓
System Detects Issues
      ↓
User Reviews Issues
      ↓
User Selects Cleaning Actions
      ↓
System Creates Clean Version
      ↓
Quality Report Generated
      ↓
User Downloads Dataset
```

### Deliverable

Initial workflow documentation.

---

# 5. PHASE 1 — Data Understanding

This phase is primarily Python and Pandas.

Do not build the web application yet.

## V1.0 — Dataset Loading

Learn and practice:

- `pd.read_csv()`
- `pd.read_excel()`

Understand:

- DataFrame
- rows
- columns
- index
- data types

### Goal

Successfully load several datasets.

---

## V1.1 — Dataset Exploration

Practice:

```python
.head()
.tail()
.shape
.columns
.dtypes
.info()
.describe()
```

Understand what each operation tells an analyst.

### Goal

Be able to inspect an unfamiliar dataset.

---

## V1.2 — Missing Data

Learn:

```python
.isna()
.isnull()
.notna()
```

Practice:

- counting missing values
- calculating missing percentages
- identifying affected columns
- identifying affected rows

### Goal

Produce a missing-value report.

---

## V1.3 — Duplicate Data

Learn:

```python
.duplicated()
.drop_duplicates()
```

Understand:

- exact duplicates
- potential duplicates
- why duplicates should not always be deleted blindly

### Goal

Identify duplicate records safely.

---

## V1.4 — Data Types

Practice detecting:

- numeric values
- text values
- dates
- booleans
- mixed-type columns

Example:

```text
Age
"25"
"31"
"unknown"
"-5"
```

### Goal

Understand why correct data types matter for analysis.

---

## V1.5 — Basic Data Cleaning Practice

Practice manually cleaning a small dataset.

Topics:

- missing values
- duplicates
- inconsistent text
- dates
- numeric conversion
- invalid values

### Goal

Understand the cleaning process before automating it.

---

# 6. PHASE 2 — Data Profiler

Now convert the knowledge from Phase 1 into reusable Python code.

## V2.0 — DataProfiler

Create a component that accepts a DataFrame and produces a profile.

Example:

```text
Rows: 10,542
Columns: 18

Missing Values: 127
Duplicate Rows: 34

Numeric Columns: 8
Text Columns: 7
Date Columns: 3
```

---

## V2.1 — Dataset-Level Statistics

Calculate:

- number of rows
- number of columns
- total missing values
- duplicate count

---

## V2.2 — Column-Level Statistics

For each column record:

- name
- data type
- number of values
- missing count
- missing percentage
- unique count

For numeric columns also consider:

- minimum
- maximum
- mean
- median
- standard deviation

---

## V2.3 — Missing-Value Report

Produce a structured report such as:

```text
Column      Missing    Percentage
email       127        1.20%
phone       42         0.40%
address     19         0.18%
```

---

## V2.4 — Duplicate Report

Report:

- duplicate row count
- duplicate percentage
- affected records

---

## V2.5 — Data-Type Report

Classify columns into categories such as:

- numeric
- text
- date
- boolean
- unknown / mixed

---

## V2.6 — Profile Output

Return the profile in a machine-readable format such as JSON.

Example structure:

```json
{
  "rows": 10542,
  "columns": 18,
  "missing_values": 127,
  "duplicates": 34
}
```

### Phase 2 Completion Criteria

The profiler should be reusable with different datasets without rewriting the analysis logic.

---

# 7. PHASE 3 — Data Quality Engine

Now the system begins answering:

> What is wrong with this dataset?

## V3.0 — Quality Issue Model

Define a quality issue concept.

Potential categories:

```text
MISSING
DUPLICATE
INVALID_FORMAT
INVALID_RANGE
INCONSISTENT_CATEGORY
INVALID_TYPE
OUTLIER
```

Each issue should have enough information to explain:

- what went wrong
- where it happened
- why it matters
- how many records are affected

---

## V3.1 — Missing-Value Checks

Detect:

- missing values
- missing percentages
- columns with excessive missingness

---

## V3.2 — Duplicate Checks

Detect:

- duplicate rows
- duplicate identifiers

---

## V3.3 — Format Validation

Support basic validation for fields such as:

- email
- phone
- date
- postal code

---

## V3.4 — Range Validation

Examples:

```text
Age < 0
Age > 120
```

Other examples can be defined according to the dataset.

---

## V3.5 — Categorical Validation

Detect inconsistent values such as:

```text
Male
male
MALE
M
```

The system should identify inconsistency rather than automatically assuming every variation is incorrect.

---

## V3.6 — Outlier Detection

Start with understandable statistical methods:

- mean
- median
- standard deviation
- IQR
- z-score

Important rule:

> An outlier is not automatically an error.

The system should flag potential outliers for review.

---

## V3.7 — Quality Issue Report

Produce something like:

```text
DATA QUALITY ISSUES

Missing Values       127
Duplicates            34
Invalid Emails        12
Invalid Ages           7
Format Issues          8
Potential Outliers    21
```

### Phase 3 Completion Criteria

The system can analyze a dataset and produce a structured list of potential quality problems.

---

# 8. PHASE 4 — Data Cleaning Engine

Now we move from detection to controlled transformation.

## V4.0 — Cleaning Strategy

Define which issues can be:

- automatically cleaned
- cleaned only with user-selected rules
- flagged for manual review

Do not automatically modify every suspicious value.

### V4.0.1 — Deterministic Pipeline Execution Order

Cleaning operations must execute in a strict, documented sequence to avoid conflicting transformations (e.g. invalid values must be identified and nullified before missing-value imputation runs):

```text
1. Ingest & Load Dataset (CSV / XLSX)
      ↓
2. Structural Normalization (strip column names, remove empty rows/columns)
      ↓
3. Whitespace & Text Trimming
      ↓
4. Categorical Standardization (configured value mappings, casing)
      ↓
5. Data Type Validation (check string representation of numbers/dates)
      ↓
6. Format Validation (regex check on emails, phones, postal codes)
      ↓
7. Range & Boundary Validation (bounds checking on numeric/date fields)
      ↓
8. Invalidation Step (coerce confirmed format/range errors to NaN/Null)
      ↓
9. Duplicate Detection & Resolution (exact or key-based deduplication)
      ↓
10. Missing-Value Handling (drop, fill with mean/median/mode, forward-fill)
      ↓
11. Strict Type Casting (convert to formal nullable types, e.g. Int64, datetime64)
      ↓
12. Post-Cleaning Assessment (calculate quality score improvements)
      ↓
13. Version Persistence (save as Parquet internally, log cleaning history)
```

---

## V4.1 — Missing-Value Handling

Support selected strategies such as:

- drop rows
- fill with mean
- fill with median
- fill with mode
- forward fill
- backward fill

The correct strategy should depend on the type and meaning of the data.

---

## V4.2 — Duplicate Removal

Provide controlled duplicate removal.

Example:

```text
Before: 10,542 rows
After:  10,508 rows

Removed: 34
```

---

## V4.3 — Text Standardization

Normalize values such as:

```text
male
Male
MALE
```

into a consistent representation when a rule has been defined.

---

## V4.4 — Date Normalization

Convert different representations into a consistent format.

Example:

```text
01/15/2026
2026-01-15
January 15, 2026
```

→

```text
2026-01-15
```

---

## V4.5 — Type Conversion

Convert values to appropriate data types when safe.

Example:

```text
"25"
"31"
"42"
```

→

```text
25
31
42
```

---

## V4.6 — Cleaning Log

Every cleaning operation should be recorded.

Example:

```text
CLEANING LOG

34 duplicate rows removed
127 missing emails detected
12 invalid emails detected
8 date formats standardized
```

The system should be able to explain what changed.

---

## V4.7 — Before / After Comparison

Show:

```text
BEFORE
Rows: 10,542
Quality: 82%

        ↓

AFTER
Rows: 10,508
Quality: 94.7%
```

### Phase 4 Completion Criteria

The system can create a cleaned dataset without destroying the original and can explain the transformations applied.

---

# 9. PHASE 5 — Data Quality Score

Now create a measurable quality summary.

## V5.0 — Quality Dimensions

Consider dimensions such as:

- Completeness
- Validity
- Consistency
- Uniqueness

Accuracy should be treated carefully because the system usually cannot know whether a value is factually correct without an external reference.

---

## V5.1 — Quality Score

Create an overall score such as:

```text
Data Quality Score
94.7%
```

**Design Principle:** Do not hardcode arbitrary weights in advance. Phase 5 is explicitly dedicated to understanding and calibrating the scoring algorithm:
- Explore how each dimension (Completeness, Validity, Consistency, Uniqueness) is mathematically normalized.
- Test different weighting strategies across sample datasets.
- Formally document the chosen formula and explain the rationale in the portfolio case study.

---

## V5.2 — Dimension Scores

Example:

```text
Completeness     97%
Validity         94%
Consistency      96%
Uniqueness       99%
```

---

## V5.3 — Quality Report

Combine:

- dataset statistics
- quality issues
- dimension scores
- overall score
- cleaning actions

### Phase 5 Completion Criteria

A user can understand the overall condition of a dataset from one report.

---

# 10. PHASE 6 — PostgreSQL & Dataset History

Only after the processing engine works independently should the database become part of the application.

## V6.0 — Database Design

Potential entities:

```text
Dataset
DatasetVersion
QualityReport
QualityIssue
CleaningJob
```

Relationships should be designed before implementation.

### V6.0.1 — Hybrid Storage Architecture

To prevent dangerous dynamic schema migrations and database bloat, the platform uses a clean hybrid separation:

```text
                  PostgreSQL
               ┌──────────────┐
               │ Dataset      │  ← Metadata (name, rows, columns, created_at)
               │ Version      │  ← Version history pointer & parent ID
               │ QualityReport│  ← Overall & dimensional quality scores
               │ QualityIssue │  ← Detected quality issues & affected columns
               │ CleaningJob  │  ← Operations performed & parameters used
               └──────────────┘

                       +

              File/Object Storage
               ┌──────────────┐
               │ raw_uuid.csv │  ← Original uploaded file
               │ v1_uuid.parquet ← Cleaned/typed snapshot (fast & schema-safe)
               │ v2_uuid.parquet ← Subsequent versions
               └──────────────┘
```

- **PostgreSQL** stores structured metadata, relationships, logs, and analytical metrics.
- **Filesystem / Object Storage** stores the actual tabular records using Apache Parquet internally.

---

## V6.1 — Dataset Records

Store:

- dataset name
- original filename
- upload date
- row count
- column count
- status

---

## V6.2 — Dataset Versions

Preserve transformations.

Example:

```text
customers.csv

Version 1
10,542 rows
Quality: 82%

        ↓ Cleaning

Version 2
10,508 rows
Quality: 94.7%
```

---

## V6.3 — Quality Reports

Store generated quality information.

---

## V6.4 — Quality Issues

Store detected issues and their status.

---

## V6.5 — Cleaning Jobs

Record:

- what operation ran
- when it ran
- which dataset version it affected
- what changed

### Phase 6 Completion Criteria

The system can preserve dataset history instead of overwriting data.

---

# 11. PHASE 7 — Django REST API

Now turn the processing system into a backend service.

## V7.0 — Django Project Setup

Create:

```text
backend/
├── manage.py
├── config/
├── datasets/
├── quality/
└── cleaning/
```

The exact application structure may be adjusted as the project develops.

---

## V7.1 — Dataset API

Potential endpoints:

```text
POST /datasets/
GET  /datasets/
GET  /datasets/{id}/
```

**Security & Authorization:** Datasets must belong to an authenticated user (`user_id`). Ensure User A cannot view, modify, or download User B's datasets (IDOR prevention).

---

## V7.2 — Profile API

```text
GET /datasets/{id}/profile/
```

---

## V7.3 — Quality API

```text
GET /datasets/{id}/quality/
GET /datasets/{id}/issues/
```

---

## V7.4 — Cleaning API

```text
POST /datasets/{id}/clean/
```

Accepts user-selected operations. A representative schema to be finalized during V7:

```json
{
  "operations": [
    {
      "column": "age",
      "action": "fill_missing",
      "strategy": "median"
    },
    {
      "column": "email",
      "action": "drop_invalid_format"
    },
    {
      "action": "drop_duplicates",
      "subset": ["id"]
    }
  ]
}
```

*Execution model:* Synchronous in-memory execution for MVP (constrained to ≤ 25 MB files). Task queues (Celery/Redis) deferred to later scaling phases.

---

## V7.5 — Version API

```text
GET /datasets/{id}/versions/
GET /datasets/{id}/versions/{version_id}/
```

---

## V7.6 — Export API

Allow the cleaned dataset to be downloaded (as CSV, with formula-injection sanitization applied).

### Phase 7 Completion Criteria

The core data-quality engine can be accessed through a documented REST API with user ownership checks.

---

# 12. PHASE 8 — React Web Application

Now create the user-facing application.

## V8.0 — Application Setup

Use:

- React
- Vite

**Design Guideline:** Keep the React frontend minimal and focused. It serves as a crisp, interactive demonstration interface for the engine, avoiding excessive frontend scaffolding or complex state machines.

---

## V8.1 — Dataset Upload

User can:

1. Select a CSV or Excel file.
2. Upload it.
3. See processing status.

---

## V8.2 — Dataset Overview

Show:

```text
Dataset Name
Rows
Columns
Missing Values
Duplicates
Quality Score
```

---

## V8.3 — Quality Issues

Show issues grouped by type.

Example:

```text
Missing Values       127
Duplicates            34
Invalid Values        12
Format Issues          8
```

---

## V8.4 — Issue Details

Allow the user to inspect affected columns/records.

---

## V8.5 — Cleaning Controls

Allow users to choose supported cleaning operations.

---

## V8.6 — Before / After View

Show the difference between the original and cleaned dataset.

---

## V8.7 — Export

Provide a way to download the cleaned dataset.

### Phase 8 Completion Criteria

A user can complete the main workflow without directly interacting with Python or the API.

---

# 13. PHASE 9 — Power BI & DAX

Power BI serves as the **Data Quality Governance & Platform Analytics** layer.

> **Scope Clarification:** Power BI connects directly to PostgreSQL metadata (`QualityReport`, `QualityIssue`, `CleaningJob`, `DatasetVersion`) to analyze the health, trends, and operational metrics of the data platform itself. It does *not* attempt to dynamically model arbitrary user tables.

## V9.0 — Understand the Data Model

Identify which tables and fields are useful for platform analytics:
- `Dataset` & `DatasetVersion` (throughput, file types, sizes)
- `QualityReport` (overall score, completeness, validity, uniqueness, consistency)
- `QualityIssue` (issue types, frequency, severity, affected columns)
- `CleaningJob` (operations performed, rows affected, quality delta)

---

## V9.1 — Connect Power BI

Connect Power BI Desktop to the PostgreSQL database (or analytical view/extracts) with a structured star/snowflake schema.

---

## V9.2 — Build the Quality Overview

Possible KPIs:

```text
Datasets Processed
Average Quality Score
Issues Detected
Issues Resolved
```

---

## V9.3 — Quality Trends

Analyze quality over time.

---

## V9.4 — Issue Breakdown

Visualize:

- missing values
- duplicates
- invalid values
- format problems
- outliers

---

## V9.5 — Dataset Comparison

Compare quality between datasets or dataset versions.

---

## V9.6 — DAX Measures

Create measures such as:

```text
Total Datasets
Average Quality Score
Total Issues
Resolved Issues
Issue Resolution Rate
Average Missing Rate
```

Additional measures should be created as the actual data model requires.

---

## V9.7 — Final Power BI Report

Suggested pages:

### Page 1 — Executive Overview

- quality score
- datasets processed
- issues
- resolution rate

### Page 2 — Data Quality

- completeness
- validity
- consistency
- uniqueness

### Page 3 — Issues

- issue categories
- affected columns
- trends

### Page 4 — Dataset History

- quality changes between versions
- cleaning impact

### Phase 9 Completion Criteria

The project can demonstrate not only data cleaning but also business-style data-quality analytics.

---

# 14. PHASE 10 — Testing

Testing should cover both the processing engine and the application.

## V10.0 — Unit Tests

Test:

- missing-value detection
- duplicate detection
- validation
- type conversion
- cleaning functions
- quality scoring

---

## V10.1 — Edge Cases

Test:

- empty dataset
- dataset with no missing values
- dataset with every value missing in a column
- duplicate-only data
- invalid dates
- mixed types
- extremely large values
- unexpected columns

---

## V10.2 — API Tests

Test:

- upload
- profile
- quality report
- cleaning
- export
- invalid requests

---

## V10.3 — Integration Tests

Test the complete workflow:

```text
Upload
 ↓
Profile
 ↓
Detect Issues
 ↓
Clean
 ↓
Create Version
 ↓
Generate Report
 ↓
Export
```

### Phase 10 Completion Criteria

The main workflow works reliably and important failure cases are covered.

---

# 15. PHASE 11 — Security & Reliability

Before deployment, review the application.

## V11.0 — File Validation

Validate uploads before feeding them to Pandas:

- **Allowed file types:** `.csv`, `.xlsx`
- **File size limit:** Strict cap (≤ 25 MB) to avoid memory exhaustion
- **MIME-type / magic byte check:** Ensure uploaded files are genuine CSV/Excel files

---

## V11.1 — Upload Safety & Path Traversal Prevention

Ensure uploaded files cannot escape the storage directory:
- Generate cryptographically secure UUID filenames for disk storage (e.g., `a8f91c2e-4b12...parquet`).
- Never use user-supplied filenames directly in filesystem path operations.
- Preserve the user's original filename purely as a display string in PostgreSQL.

---

## V11.2 — API Authorization & IDOR Prevention

Ensure data isolation:
- Require authentication for dataset operations.
- Enforce strict ownership filters: User A cannot inspect, clean, download, or delete User B's dataset IDs.

---

## V11.3 — CSV Formula Injection Defense

Protect users downloading cleaned CSV files:
- When exporting tabular data to CSV, sanitize cells starting with formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`) by prepending a single quote `'` or a space so spreadsheet software (Excel/Calc) cannot execute arbitrary commands.

---

## V11.4 — Secrets Management

Do not commit:

- database credentials
- Django `SECRET_KEY`
- API keys or debug flags

Use environment variables (`.env`) loaded through a library like `python-dotenv` or `django-environ`.

---

## V11.5 — Error Handling

Return clean, structured JSON errors with appropriate HTTP status codes (400, 403, 404, 500) without leaking stack traces or internal server paths.

---

# 16. PHASE 12 — Deployment

Deployment provider will be selected once the application is stable.

## V12.0 — Production Configuration

Prepare:

- environment variables
- production settings
- allowed hosts
- CORS
- database configuration
- static files
- media/file storage

---

## V12.1 — Production Database

Configure PostgreSQL for production.

---

## V12.2 — Backend Deployment

Deploy Django/API.

---

## V12.3 — Frontend Deployment

Deploy React application.

---

## V12.4 — File Storage

If required by the deployment environment, move uploaded files from local storage to suitable object storage.

---

## V12.5 — Production Testing

Test:

- login / access if implemented
- upload
- profiling
- cleaning
- reports
- export

### Phase 12 Completion Criteria

The application is accessible in a production environment and the main workflow works outside the development machine.

---

# 17. PHASE 13 — Documentation

The project should be documented as a real engineering/data project.

## V13.0 — README

Include:

- project overview
- problem
- solution
- features
- architecture
- technology stack
- workflow
- screenshots
- installation
- environment configuration
- testing
- deployment
- future improvements

---

## V13.1 — Architecture Diagram

Document:

```text
React
  ↓
Django REST API
  ↓
Data Quality Engine
  ↓
PostgreSQL
  ↓
Power BI
```

---

## V13.2 — Data Flow Diagram

Document:

```text
Raw Dataset
    ↓
Ingestion
    ↓
Profiling
    ↓
Quality Detection
    ↓
Cleaning
    ↓
Versioning
    ↓
Analytics
```

---

## V13.3 — Cleaning Rules Documentation

Document every supported cleaning operation and its behavior.

---

# 18. PHASE 14 — Portfolio Preparation

## V14.0 — Project Case Study

Explain:

### Problem

Poor-quality data can produce unreliable analysis.

### Solution

A platform that profiles datasets, detects quality problems, performs controlled cleaning, preserves dataset versions, and provides quality analytics.

### Technical Work

- Python
- Pandas
- PostgreSQL
- Django REST Framework
- React
- Power BI
- DAX

---

## V14.1 — Screenshots

Capture:

- upload screen
- profile
- quality report
- issues
- cleaning results
- before/after
- Power BI dashboard

---

## V14.2 — GitHub

Repository should contain:

```text
project/
├── backend/
├── frontend/
├── data/
├── docs/
├── tests/
├── .env.example
├── .gitignore
└── README.md
```

Do not commit private datasets or secrets.

---

## V14.3 — Resume Entry

The final resume description should emphasize measurable work rather than simply listing technologies.

Potential themes:

- automated data profiling
- data-quality detection
- cleaning pipeline
- dataset versioning
- Power BI analytics
- DAX
- REST API

The final wording should be written after the actual project is complete so that it accurately reflects what was built.

---

# 19. Final V1.0 Definition of Done

The project is considered complete when a user can:

```text
1. Upload a dataset
        ↓
2. System profiles the dataset
        ↓
3. System detects quality issues
        ↓
4. User reviews issues
        ↓
5. User selects cleaning operations
        ↓
6. System creates a cleaned version
        ↓
7. Original data remains preserved
        ↓
8. System records cleaning history
        ↓
9. System calculates a quality report
        ↓
10. User downloads the cleaned dataset
        ↓
11. Power BI analyzes the quality data
```

---

# 20. Version Roadmap

The project follows a **Phase-based versioning system** where every version maps 1:1 with its learning phase:

| Phase | Version | Milestone Goal | Focus Area |
|---|---|---|---|
| **Phase 0** | **V0.x** | Project Definition & Scope | Specifications, MVP boundaries, workflow |
| **Phase 1** | **V1.x** | Data Understanding | Python, Pandas fundamentals, loading, manual cleaning |
| **Phase 2** | **V2.x** | Data Profiler | Reusable profiling engine (rows, cols, stats, dtypes) |
| **Phase 3** | **V3.x** | Data Quality Engine | Issue models, validation checks (formats, ranges, outliers) |
| **Phase 4** | **V4.x** | Data Cleaning Engine | 13-step deterministic transformation pipeline |
| **Phase 5** | **V5.x** | Data Quality Scoring | Multi-dimensional scoring formula design & calibration |
| **Phase 6** | **V6.x** | PostgreSQL & History | Hybrid storage (Postgres metadata + Parquet files) |
| **Phase 7** | **V7.x** | Django REST API | Clean REST endpoints, user dataset ownership, JSON specs |
| **Phase 8** | **V8.x** | React Interface | Minimal single-page dashboard UI (Vite + React) |
| **Phase 9** | **V9.x** | Power BI & DAX | Platform quality governance, KPI dashboards & DAX |
| **Phase 10** | **V10.x** | Testing Suite | Automated pytest coverage (engine, edge cases, API) |
| **Phase 11** | **V11.x** | Security & Hardening | File validation, UUID paths, CSV sanitization, auth |
| **Phase 12** | **V12.x** | Deployment | Environment variables, cloud hosting, production DB |
| **Phase 13** | **V13.x** | Documentation | Engineering README, architecture & data flow diagrams |
| **Phase 14** | **V14.x** | Portfolio Preparation | Case study writeup, screenshots, demo video, resume |

---

# 21. Learning Path

The project intentionally follows this progression:

```text
Python
  ↓
Pandas
  ↓
Data Cleaning
  ↓
Data Profiling
  ↓
Data Quality
  ↓
ETL Concepts
  ↓
SQL
  ↓
PostgreSQL
  ↓
Django REST Framework
  ↓
React
  ↓
Testing
  ↓
Power BI
  ↓
DAX
  ↓
Deployment
```

The purpose is not to learn every technology simultaneously.

Each technology is introduced when the project actually needs it.

---

# 22. Recommended Development Philosophy

Do not ask:

> "How can I finish this project as quickly as possible?"

Ask:

> "What concept am I supposed to learn at this step, and why does the project need it?"

The project should be developed slowly enough that every major component is understandable.

### Core Focus vs. Supporting Layers

Remember the engineering hierarchy to prevent over-extension:

- **Core Star (V1–V5):** Learn data analysis, validation, profiling, and quality scoring deeply.
- **Data Infrastructure (V6):** Cleanly separate PostgreSQL metadata from Parquet files.
- **Application Layer (V7–V8):** Keep Django & React minimal — they exist to expose the engine, not to become a complex SaaS.
- **Business Intelligence (V9):** Showcase high-level data governance and DAX modeling in Power BI.
- **Production Polish (V10–V14):** Test, secure, deploy, and package as a standout portfolio piece.

---

# 23. Starting Point

The project begins at:

## **PHASE 0 — V0.1: Project Definition**

Before writing application code, define:

1. The exact problem.
2. The target user.
3. Supported dataset types.
4. Quality problems to detect.
5. Cleaning operations.
6. MVP boundaries.
7. Expected workflow.

Only after this is finalized should implementation begin.

---

## Final Project Concept

> **A data-quality and cleaning platform that helps users determine whether a dataset is trustworthy before using it for analysis.**

The project combines **data analysis, data cleaning, backend engineering, database design, web development, and BI** into one continuous workflow.
