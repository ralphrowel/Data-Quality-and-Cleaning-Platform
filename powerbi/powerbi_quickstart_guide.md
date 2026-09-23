# Power BI Connection & Setup Quickstart Guide

**Phase 9: V9.1 — V9.7**  
**Layer:** Platform Governance & Quality Analytics  
**Supported Tools:** Power BI Desktop (Windows), Power BI Service, Excel Power Pivot  

---

## Option 1: 1-Click Folder Import (Fastest & Recommended)

All Star Schema analytical tables are pre-extracted in [`powerbi/data/`](file:///c:/Users/ralph/OneDrive/Desktop/Data%20Analyst/Data%20Quality%20&%20Cleaning%20Platform/powerbi/data).

1. Launch **Power BI Desktop**.
2. Click **Get Data** -> **Folder** (or **Text/CSV** for individual files).
3. Select the folder path:
   ```text
   C:\Users\ralph\OneDrive\Desktop\Data Analyst\Data Quality & Cleaning Platform\powerbi\data
   ```
4. Load the following tables:
   - `Dim_Dataset.csv`
   - `Dim_Version.csv`
   - `Dim_Date.csv`
   - `Dim_Severity.csv`
   - `Dim_Grade.csv`
   - `Fact_QualityEvaluation.csv`
   - `Fact_QualityIssues.csv`
   - `Fact_CleaningJobs.csv`

---

## Option 2: 1-Click Flat Table (Rapid Prototype)

If you wish to immediately test visuals without configuring multi-table relationships:
1. Click **Get Data** -> **Text/CSV**.
2. Select [`Platform_Quality_Analytics_Flat.csv`](file:///c:/Users/ralph/OneDrive/Desktop/Data%20Analyst/Data%20Quality%20&%20Cleaning%20Platform/powerbi/data/Platform_Quality_Analytics_Flat.csv).
3. Click **Load** and start dragging dimensions and metrics directly into charts.

---

## Option 3: Direct SQLite / PostgreSQL Live Connection

If connecting directly to the running database engine:

### For SQLite (`data/platform.db`):
1. Install the official **SQLite ODBC Driver** (64-bit).
2. In Power BI Desktop: **Get Data** -> **ODBC**.
3. Connection string:
   ```text
   driver={SQLite3 ODBC Driver};Database=C:\Users\ralph\OneDrive\Desktop\Data Analyst\Data Quality & Cleaning Platform\data\platform.db;
   ```

### For PostgreSQL (When deployed):
1. In Power BI Desktop: **Get Data** -> **PostgreSQL database**.
2. Server: `localhost:5432` | Database: `data_quality_platform`.
3. Import the 5 tables defined in [`docs/schema.sql`](file:///c:/Users/ralph/OneDrive/Desktop/Data%20Analyst/Data%20Quality%20&%20Cleaning%20Platform/docs/schema.sql).

---

## Setting Up Relationships in Model View

Switch to the **Model View** tab in Power BI Desktop and configure the relationships as shown below:

```text
[Dim_Dataset]   (dataset_id) 1 ──< * (dataset_id) [Fact_QualityEvaluation]
[Dim_Version]   (version_id) 1 ──< * (version_id) [Fact_QualityEvaluation]
[Dim_Grade]     (grade)      1 ──< * (grade)      [Fact_QualityEvaluation]
[Dim_Date]      (DateKey)    1 ──< * (date_key)   [Fact_QualityEvaluation]

[Dim_Dataset]   (dataset_id) 1 ──< * (dataset_id) [Fact_QualityIssues]
[Dim_Version]   (version_id) 1 ──< * (version_id) [Fact_QualityIssues]
[Dim_Severity]  (severity_c) 1 ──< * (severity_c) [Fact_QualityIssues]
[Dim_Date]      (DateKey)    1 ──< * (date_key)   [Fact_QualityIssues]

[Dim_Dataset]   (dataset_id) 1 ──< * (dataset_id) [Fact_CleaningJobs]
[Dim_Date]      (DateKey)    1 ──< * (date_key)   [Fact_CleaningJobs]
[Dim_Version]   (version_id) 1 ──< * (target_v_id)[Fact_CleaningJobs] (Active)
[Dim_Version]   (version_id) 1 ──< * (source_v_id)[Fact_CleaningJobs] (Inactive)
```
*(All relationship cross-filter directions should be set to **Single: Dimension filters Fact**).*

---

## Adding the DAX Measures

1. In the **Home** tab, click **Enter Data**.
2. Name the table `_Measures` and click **Load**.
3. Right-click `_Measures` and select **New Measure**.
4. Open [`powerbi/dax_measures.md`](file:///c:/Users/ralph/OneDrive/Desktop/Data%20Analyst/Data%20Quality%20&%20Cleaning%20Platform/powerbi/dax_measures.md) and copy each measure formula directly into the formula bar.
5. Set the recommended format string (e.g. `0.0%` for percentages, `#,##0` for integer counts).

---

## Refreshing Data After Uploading / Cleaning Datasets

Whenever new datasets are uploaded or cleaned via the React dashboard or CLI:
1. Run the ETL script from the terminal:
   ```powershell
   .venv\Scripts\python.exe scripts/export_powerbi_data.py
   ```
2. In Power BI Desktop, click **Home** -> **Refresh**.
3. All dashboard metrics, issue counts, and delta scores will automatically update!
