# Power BI 4-Page Report Design Specification

**Phase 9: V9.2 — V9.5, V9.7**  
**Layer:** Platform Governance & Quality Analytics  
**Resolution:** 16:9 Standard Widescreen (1280 × 720 px or 1920 × 1080 px)  
**Theme:** Sleek Dark Analytics / Glassmorphism Aesthetic (`#070B14` Dark Charcoal Background with Vibrant Accents)

---

## 🎨 Global Palette & Typography

- **Background:** `#070B14` / `#0F172A`
- **Surface Cards:** `#1E293B` (70% opacity, 1px border `#334155`)
- **Primary Text:** `#F8FAFC`
- **Secondary Text:** `#94A3B8`
- **Accent Emerald (Grade A / Success):** `#10B981`
- **Accent Cyan (Grade B / Primary):** `#38BDF8`
- **Accent Amber (Grade C / Warning):** `#F59E0B`
- **Accent Orange (Grade D / Caution):** `#F97316`
- **Accent Red (Grade F / Critical):** `#EF4444`
- **Font Family:** `Segoe UI Semibold` (Headers), `Segoe UI` (Body), `Consolas` / `Segoe UI Mono` (Values)

---

## Page 1: Executive Overview & Governance Cockpit

**Goal:** Answer executive stakeholders: *"What is the aggregate trust rating of all datasets across the organization, and what is our readiness for BI & analytics?"*

### Top Banner & Filters (Y: 0 to 110 px)
- **Title Block:** `Platform Governance & Data Quality Cockpit` | Subtitle: `Continuous Multi-Dimensional Data Verification`
- **Slicers:**
  - Date Range (`Dim_Date[FullDate]`) — Between Slicer
  - File Format Type (`Dim_Dataset[file_format_type]`) — Horizontal Tile Buttons (CSV / Excel / All)
  - Grade Tier (`Dim_Grade[grade]`) — Dropdown

### KPI Ribbon (Y: 120 to 220 px — 5 Card Visuals)
1. **Total Monitored Datasets:** `[Total Datasets]` (Callout: `10`, Subtext: `+2 this week`)
2. **Total Monitored Records:** `[Total Records Monitored]` (Callout: `8,807+`, Subtext: `Active latest versions`)
3. **Enterprise Quality Score:** `[Latest Quality Score]` (Callout: `84.8%`, Conditional color: Cyan `#38BDF8`)
4. **Trustworthy Compliance Rate:** `[Trustworthy Rate %]` (Callout: `70.0%`, Goal: `≥ 80.0%`)
5. **Total Issues Detected:** `[Total Issues Detected]` (Callout: `28`, Subtext: `14 Critical`)

### Core Visuals Grid (Y: 230 to 700 px)
- **Left Visual (W: 400 px, H: 450 px) — Donut Chart:**
  - *Title:* `Dataset Trust Tier Distribution`
  - *Legend:* `Dim_Grade[grade_name]`
  - *Values:* `[Total Datasets]`
  - *Colors:* Grade A (`#10B981`), Grade B (`#38BDF8`), Grade C (`#F59E0B`), Grade D (`#F97316`), Grade F (`#EF4444`)
  - *Center KPI:* `[Trustworthy Rate %]`

- **Middle Visual (W: 460 px, H: 450 px) — Radar / Clustered Bar Chart:**
  - *Title:* `4-Dimension Organizational Scorecard`
  - *X-Axis / Values:* `[Avg Completeness Score]`, `[Avg Validity Score]`, `[Avg Uniqueness Score]`, `[Avg Consistency Score]`
  - *Data Labels:* Enabled (`0.0%`)
  - *Threshold Line:* 80.0% Benchmark (Dotted line in `#38BDF8`)

- **Right Visual (W: 380 px, H: 450 px) — Ranked Table:**
  - *Title:* `Datasets Requiring Remediation (Action List)`
  - *Columns:* `Dim_Dataset[dataset_name]`, `Dim_Grade[grade]`, `[Latest Quality Score]`, `[Critical Issues]`
  - *Conditional Formatting:* Background color on `[Latest Quality Score]` with gradient (Red -> Amber -> Green)

---

## Page 2: Data Quality Dimensions Deep-Dive

**Goal:** Provide analytics engineers and data quality leads with granular inspection into the 4 calibrated quality pillars.

### Layout
- **Top Metric Cards (4 Cards across X-axis):**
  1. **Completeness (30% Weight):** `[Avg Completeness Score]` | Benchmark: `95.0%`
  2. **Validity (30% Weight):** `[Avg Validity Score]` | Benchmark: `90.0%`
  3. **Uniqueness (20% Weight):** `[Avg Uniqueness Score]` | Benchmark: `98.0%`
  4. **Consistency (20% Weight):** `[Avg Consistency Score]` | Benchmark: `90.0%`

- **Visual 1 (Top Left, W: 600 px, H: 280 px) — 100% Stacked Area Chart:**
  - *Title:* `Dimension Score Evolution Over Time`
  - *X-Axis:* `Dim_Date[FullDate]`
  - *Values:* `[Avg Completeness Score]`, `[Avg Validity Score]`, `[Avg Uniqueness Score]`, `[Avg Consistency Score]`

- **Visual 2 (Top Right, W: 640 px, H: 280 px) — Clustered Column Chart:**
  - *Title:* `Dimension Performance by Dataset`
  - *X-Axis:* `Dim_Dataset[dataset_name]`
  - *Y-Axis (Multi-Metric):* 4 Dimension Measures

- **Visual 3 (Bottom, Full Width, W: 1240 px, H: 240 px) — Matrix Visual:**
  - *Rows:* `Dim_Dataset[dataset_name]`, `Dim_Version[version_label]`
  - *Values:* `[Avg Quality Score]`, `[Avg Completeness Score]`, `[Avg Validity Score]`, `[Avg Uniqueness Score]`, `[Avg Consistency Score]`
  - *Conditional Formatting:* In-cell Data Bars for each metric

---

## Page 3: Anomaly & Issue Diagnostics

**Goal:** Identify root causes of dirty data, pinpoint defective columns, and track severity breakdown.

### Layout
- **Top KPI Cards:**
  1. `[Critical Issues]` (Red `#EF4444`)
  2. `[Warning Issues]` (Amber `#F59E0B`)
  3. `[Info Issues]` (Cyan `#38BDF8`)
  4. `[Total Defective Rows]` (Whole number)

- **Visual 1 (Left, W: 500 px, H: 450 px) — Pareto Bar Chart:**
  - *Title:* `Defect Frequency by Category (Pareto Analysis)`
  - *Y-Axis:* `Fact_QualityIssues[issue_category]` (e.g. `MISSING_VALUES`, `DUPLICATES`, `INVALID_FORMAT`)
  - *X-Axis / Column Value:* `COUNT(Fact_QualityIssues[issue_id])`
  - *Line Value:* Cumulative % of Issues

- **Visual 2 (Middle, W: 400 px, H: 450 px) — Treemap:**
  - *Title:* `Affected Columns Heatmap`
  - *Category:* `Fact_QualityIssues[column_name]`
  - *Values:* `SUM(Fact_QualityIssues[affected_count])`
  - *Details:* Top problematic columns (e.g. `director`, `cast`, `country`, `date_added`)

- **Visual 3 (Right, W: 340 px, H: 450 px) — Issue Detail Card / Table:**
  - *Title:* `Defect Log & Remediation Guidance`
  - *Columns:* `Severity`, `Column`, `Description`, `Affected Rows`
  - *Filter:* Interactive cross-filtering from the Pareto and Treemap visuals

---

## Page 4: Dataset History & Cleaning Impact (ROI)

**Goal:** Prove the value of the 13-step deterministic cleaning engine by measuring before-and-after lift in data health and storage optimization.

### Layout
- **ROI Executive Callouts (Top Ribbon):**
  1. **Total Cleaning Pipelines Executed:** `[Total Cleaning Jobs]`
  2. **Total Rows Sanitized & Imputed:** `[Total Rows Remediated]`
  3. **Duplicate Rows Purged:** `[Total Duplicates Removed]`
  4. **Average Quality Lift:** `[Avg Quality Score Delta]` (Formatted in Emerald green `+12.4%`)

- **Visual 1 (Left, W: 600 px, H: 450 px) — Dumbbell / Slope Chart (or Clustered Bar):**
  - *Title:* `Before vs. After Quality Score Comparison`
  - *Y-Axis:* `Dim_Dataset[dataset_name]`
  - *Series 1 (Raw Ingestion):* `[Raw Quality Score]` (Gray / Red)
  - *Series 2 (After Cleaning):* `[Cleaned Quality Score]` (Cyan / Emerald)
  - *Data Labels:* Shows the delta jump (e.g. `82.4% -> 96.6%`)

- **Visual 2 (Right, W: 640 px, H: 450 px) — Lineage Transformation Table:**
  - *Title:* `Audit Trail & Transformation Log`
  - *Columns:*
    - `Dataset Name`
    - `Job Timestamp`
    - `Source Version (Raw)`
    - `Target Version (Parquet)`
    - `Operations Run`
    - `Rows Modified`
    - `Score Delta` (`+X.X%`)
  - *Conditional Formatting:* Green icon for positive quality delta
