# Power BI DAX Measures Library

**Phase 9: V9.6**  
**Layer:** Platform Governance & Quality Analytics  
**Table Location:** Store all measures in a dedicated `_Measures` table.

---

## 1. Core Platform KPIs

### Total Datasets Processed
```dax
Total Datasets = 
DISTINCTCOUNT(Dim_Dataset[dataset_id])
```
*Format:* `#,##0`  
*Description:* Total unique logical datasets ingested into the platform.

### Total Versions Analyzed
```dax
Total Versions Analyzed = 
COUNTROWS(Dim_Version)
```
*Format:* `#,##0`  
*Description:* Total dataset snapshots evaluated (includes raw ingestions and transformed versions).

### Total Records Monitored
```dax
Total Records Monitored = 
CALCULATE(
    SUM(Fact_QualityEvaluation[row_count]),
    Dim_Version[is_latest_version] = 1
)
```
*Format:* `#,##0`  
*Description:* Total active records currently governed across the latest version of all datasets.

### Average Quality Score
```dax
Avg Quality Score = 
AVERAGE(Fact_QualityEvaluation[overall_score])
```
*Format:* `0.0"%" `  
*Description:* Mean overall quality score across all evaluated snapshots.

### Latest Quality Score
```dax
Latest Quality Score = 
CALCULATE(
    [Avg Quality Score],
    Dim_Version[is_latest_version] = 1
)
```
*Format:* `0.0"%" `  
*Description:* Current mean quality score for active, production-ready dataset versions.

### Trustworthy Datasets Count
```dax
Trustworthy Datasets = 
CALCULATE(
    DISTINCTCOUNT(Fact_QualityEvaluation[dataset_id]),
    Fact_QualityEvaluation[is_trustworthy] = 1,
    Dim_Version[is_latest_version] = 1
)
```
*Format:* `#,##0`  
*Description:* Count of active datasets meeting or exceeding the 80.0% Grade B threshold.

### Trustworthy Rate %
```dax
Trustworthy Rate % = 
DIVIDE([Trustworthy Datasets], [Total Datasets], 0)
```
*Format:* `0.0%`  
*Description:* Proportion of enterprise datasets approved for downstream BI / ML consumption.

---

## 2. Dimensional Quality Health

### Average Completeness Score
```dax
Avg Completeness Score = 
CALCULATE(
    AVERAGE(Fact_QualityEvaluation[completeness_score]),
    Dim_Version[is_latest_version] = 1
)
```
*Format:* `0.0"%" `  
*Description:* Measures absence of unexpected nulls and missing values across all monitored attributes (Weight: 30%).

### Average Validity Score
```dax
Avg Validity Score = 
CALCULATE(
    AVERAGE(Fact_QualityEvaluation[validity_score]),
    Dim_Version[is_latest_version] = 1
)
```
*Format:* `0.0"%" `  
*Description:* Measures conformance to data types, regex patterns, and range boundaries (Weight: 30%).

### Average Uniqueness Score
```dax
Avg Uniqueness Score = 
CALCULATE(
    AVERAGE(Fact_QualityEvaluation[uniqueness_score]),
    Dim_Version[is_latest_version] = 1
)
```
*Format:* `0.0"%" `  
*Description:* Measures absence of duplicate primary keys and identical row records (Weight: 20%).

### Average Consistency Score
```dax
Avg Consistency Score = 
CALCULATE(
    AVERAGE(Fact_QualityEvaluation[consistency_score]),
    Dim_Version[is_latest_version] = 1
)
```
*Format:* `0.0"%" `  
*Description:* Measures date standardization, case uniformity, and categorical harmonization (Weight: 20%).

### Weakest Dimension Indicator
```dax
Weakest Dimension = 
VAR Comp = [Avg Completeness Score]
VAR Val = [Avg Validity Score]
VAR Uniq = [Avg Uniqueness Score]
VAR Cons = [Avg Consistency Score]
VAR MinScore = MIN(MIN(Comp, Val), MIN(Uniq, Cons))
RETURN
    SWITCH(
        TRUE(),
        MinScore = Comp, "Completeness (" & FORMAT(Comp, "0.0%") & ")",
        MinScore = Val, "Validity (" & FORMAT(Val, "0.0%") & ")",
        MinScore = Uniq, "Uniqueness (" & FORMAT(Uniq, "0.0%") & ")",
        "Consistency (" & FORMAT(Cons, "0.0%") & ")"
    )
```
*Format:* `Text`  
*Description:* Diagnoses which of the 4 dimensions requires organizational remediation.

---

## 3. Anomaly & Issue Diagnostics

### Total Issues Detected
```dax
Total Issues Detected = 
COUNTROWS(Fact_QualityIssues)
```
*Format:* `#,##0`  
*Description:* Total anomaly instances discovered by the issue detection engine.

### Critical Issues Count
```dax
Critical Issues = 
CALCULATE(
    COUNTROWS(Fact_QualityIssues),
    Dim_Severity[severity_code] = "CRITICAL"
)
```
*Format:* `#,##0`  
*Description:* High-severity defects (e.g. duplicate primary keys, null required identifiers).

### Warning Issues Count
```dax
Warning Issues = 
CALCULATE(
    COUNTROWS(Fact_QualityIssues),
    Dim_Severity[severity_code] = "WARNING"
)
```
*Format:* `#,##0`  
*Description:* Moderate defects (e.g. statistical outliers, inconsistent date formats).

### Info Issues Count
```dax
Info Issues = 
CALCULATE(
    COUNTROWS(Fact_QualityIssues),
    Dim_Severity[severity_code] = "INFO"
)
```
*Format:* `#,##0`  
*Description:* Non-breaking anomalies (e.g. leading/trailing whitespace, casing irregularities).

### Critical Issue Rate %
```dax
Critical Issue Rate % = 
DIVIDE([Critical Issues], [Total Issues Detected], 0)
```
*Format:* `0.0%`  
*Description:* Percentage of platform issues classified as blocking or critical.

### Total Defective Rows Impacted
```dax
Total Defective Rows = 
SUM(Fact_QualityIssues[affected_count])
```
*Format:* `#,##0`  
*Description:* Cumulative count of individual rows affected across all detected issues.

---

## 4. Transformation Lineage & Cleaning ROI

### Total Cleaning Jobs Executed
```dax
Total Cleaning Jobs = 
COUNTROWS(Fact_CleaningJobs)
```
*Format:* `#,##0`  
*Description:* Total deterministic cleaning pipelines executed by platform users.

### Total Rows Remediated
```dax
Total Rows Remediated = 
SUM(Fact_CleaningJobs[rows_modified])
```
*Format:* `#,##0`  
*Description:* Cumulative rows cleaned, standardized, or imputed by deterministic transformations.

### Total Duplicate Rows Eliminated
```dax
Total Duplicates Removed = 
SUM(Fact_CleaningJobs[rows_removed])
```
*Format:* `#,##0`  
*Description:* Total redundant or duplicate records safely expunged.

### Average Quality Score Delta
```dax
Avg Quality Score Delta = 
AVERAGE(Fact_CleaningJobs[quality_score_delta])
```
*Format:* `+0.0"%" ; -0.0"%" ; 0.0"%" `  
*Description:* Mean percentage-point improvement in quality score after cleaning.

### Raw vs. Cleaned Quality Delta (Dataset Level)
```dax
Raw Quality Score = 
CALCULATE(
    [Avg Quality Score],
    Dim_Version[version_number] = 1
)
```

```dax
Cleaned Quality Score = 
CALCULATE(
    [Avg Quality Score],
    Dim_Version[version_number] > 1,
    Dim_Version[is_latest_version] = 1
)
```

```dax
Cleaning Net Lift % = 
[Cleaned Quality Score] - [Raw Quality Score]
```
*Format:* `+0.0"%" ; -0.0"%" ; 0.0"%" `  
*Description:* Direct ROI measure demonstrating platform value to business stakeholders.

---

## 5. UI Color Formatting & Dynamic Badges

### Grade Color Dynamic Hex
```dax
Grade Color Hex = 
VAR Score = [Latest Quality Score]
RETURN
    SWITCH(
        TRUE(),
        Score >= 90.0, "#10B981", -- Emerald A
        Score >= 80.0, "#38BDF8", -- Cyan B
        Score >= 70.0, "#F59E0B", -- Amber C
        Score >= 60.0, "#F97316", -- Orange D
        "#EF4444"                 -- Red F
    )
```

### Trust Status Badge Text
```dax
Trust Status Badge = 
IF(
    [Latest Quality Score] >= 80.0,
    "🟢 TRUSTED FOR PRODUCTION",
    "🔴 UNTRUSTED / NEEDS CLEANING"
)
```
