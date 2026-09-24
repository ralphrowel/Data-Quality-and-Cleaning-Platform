"""Power BI Model Repair & DAX Ingestion Script.

Applies the verified Star Schema relationship graph and ingests all 23 DAX measures
into powerbi/Data_Quality_Platform_Governance.pbix.
"""

import json
from pathlib import Path
import sys
import uuid
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


pbix_path = Path("powerbi/Data_Quality_Platform_Governance.pbix")
backup_path = Path("powerbi/Data_Quality_Platform_Governance.pbix.bak")

# Ensure backup exists
if not backup_path.exists():
    import shutil
    shutil.copy2(pbix_path, backup_path)
    print(f"Created backup: {backup_path}")

with zipfile.ZipFile(pbix_path, "r") as zin:
    file_map = {f: zin.read(f) for f in zin.namelist()}

schema = json.loads(file_map["DataModelSchema"].decode("utf-16le"))
model = schema["model"]

# 1. Relationships Configuration (Strict Kimball Star Schema)
star_relationships = [
    {
        "name": "Rel_FactQE_Dataset",
        "fromTable": "Fact_QualityEvaluation",
        "fromColumn": "dataset_id",
        "toTable": "Dim_Dataset",
        "toColumn": "dataset_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactQE_Version",
        "fromTable": "Fact_QualityEvaluation",
        "fromColumn": "version_id",
        "toTable": "Dim_Version",
        "toColumn": "version_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactQE_Date",
        "fromTable": "Fact_QualityEvaluation",
        "fromColumn": "date_key",
        "toTable": "Dim_Date",
        "toColumn": "DateKey",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactQE_Grade",
        "fromTable": "Fact_QualityEvaluation",
        "fromColumn": "grade",
        "toTable": "Dim_Grade",
        "toColumn": "grade",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactQI_Dataset",
        "fromTable": "Fact_QualityIssues",
        "fromColumn": "dataset_id",
        "toTable": "Dim_Dataset",
        "toColumn": "dataset_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactQI_Version",
        "fromTable": "Fact_QualityIssues",
        "fromColumn": "version_id",
        "toTable": "Dim_Version",
        "toColumn": "version_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactQI_Date",
        "fromTable": "Fact_QualityIssues",
        "fromColumn": "date_key",
        "toTable": "Dim_Date",
        "toColumn": "DateKey",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactQI_Severity",
        "fromTable": "Fact_QualityIssues",
        "fromColumn": "severity_code",
        "toTable": "Dim_Severity",
        "toColumn": "severity_code",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactCJ_Dataset",
        "fromTable": "Fact_CleaningJobs",
        "fromColumn": "dataset_id",
        "toTable": "Dim_Dataset",
        "toColumn": "dataset_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactCJ_Date",
        "fromTable": "Fact_CleaningJobs",
        "fromColumn": "date_key",
        "toTable": "Dim_Date",
        "toColumn": "DateKey",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactCJ_TargetVersion",
        "fromTable": "Fact_CleaningJobs",
        "fromColumn": "target_version_id",
        "toTable": "Dim_Version",
        "toColumn": "version_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": True,
    },
    {
        "name": "Rel_FactCJ_SourceVersion",
        "fromTable": "Fact_CleaningJobs",
        "fromColumn": "source_version_id",
        "toTable": "Dim_Version",
        "toColumn": "version_id",
        "crossFilteringBehavior": "oneDirection",
        "isActive": False,
    },
]

# Preserve non-colliding LocalDateTable relationships
local_date_rels = [
    r for r in model.get("relationships", [])
    if "LocalDateTable" in r.get("toTable", "")
]

model["relationships"] = local_date_rels + star_relationships

# 2. Comprehensive DAX Measures Library (23 measures across 5 categories)
measures_list = [
    # Category 1: Core Platform KPIs
    {
        "name": "Total Datasets",
        "expression": "DISTINCTCOUNT(Dim_Dataset[dataset_id])",
        "formatString": "#,##0",
    },
    {
        "name": "Total Versions Analyzed",
        "expression": "COUNTROWS(Dim_Version)",
        "formatString": "#,##0",
    },
    {
        "name": "Total Records Monitored",
        "expression": "CALCULATE(SUM(Fact_QualityEvaluation[row_count]), Dim_Version[is_latest_version] = 1)",
        "formatString": "#,##0",
    },
    {
        "name": "Avg Quality Score",
        "expression": "DIVIDE(AVERAGE(Fact_QualityEvaluation[overall_score]), 100, 0)",
        "formatString": "0.0%",
    },
    {
        "name": "Latest Quality Score",
        "expression": "CALCULATE([Avg Quality Score], Dim_Version[is_latest_version] = 1)",
        "formatString": "0.0%",
    },
    {
        "name": "Trustworthy Datasets",
        "expression": "CALCULATE(DISTINCTCOUNT(Fact_QualityEvaluation[dataset_id]), Fact_QualityEvaluation[is_trustworthy] = 1, Dim_Version[is_latest_version] = 1)",
        "formatString": "#,##0",
    },
    {
        "name": "Trustworthy Rate %",
        "expression": "DIVIDE([Trustworthy Datasets], [Total Datasets], 0)",
        "formatString": "0.0%",
    },

    # Category 2: Dimensional Quality Health
    {
        "name": "Avg Completeness Score",
        "expression": "CALCULATE(DIVIDE(AVERAGE(Fact_QualityEvaluation[completeness_score]), 100, 0), Dim_Version[is_latest_version] = 1)",
        "formatString": "0.0%",
    },
    {
        "name": "Avg Validity Score",
        "expression": "CALCULATE(DIVIDE(AVERAGE(Fact_QualityEvaluation[validity_score]), 100, 0), Dim_Version[is_latest_version] = 1)",
        "formatString": "0.0%",
    },
    {
        "name": "Avg Uniqueness Score",
        "expression": "CALCULATE(DIVIDE(AVERAGE(Fact_QualityEvaluation[uniqueness_score]), 100, 0), Dim_Version[is_latest_version] = 1)",
        "formatString": "0.0%",
    },
    {
        "name": "Avg Consistency Score",
        "expression": "CALCULATE(DIVIDE(AVERAGE(Fact_QualityEvaluation[consistency_score]), 100, 0), Dim_Version[is_latest_version] = 1)",
        "formatString": "0.0%",
    },
    {
        "name": "Weakest Dimension",
        "expression": [
            "VAR Comp = [Avg Completeness Score]",
            "VAR Val = [Avg Validity Score]",
            "VAR Uniq = [Avg Uniqueness Score]",
            "VAR Cons = [Avg Consistency Score]",
            "VAR MinScore = MIN(MIN(Comp, Val), MIN(Uniq, Cons))",
            "RETURN",
            "    SWITCH(",
            "        TRUE(),",
            "        MinScore = Comp, \"Completeness (\" & FORMAT(Comp, \"0.0%\") & \")\",",
            "        MinScore = Val, \"Validity (\" & FORMAT(Val, \"0.0%\") & \")\",",
            "        MinScore = Uniq, \"Uniqueness (\" & FORMAT(Uniq, \"0.0%\") & \")\",",
            "        \"Consistency (\" & FORMAT(Cons, \"0.0%\") & \")\"",
            "    )",
        ],
    },

    # Category 3: Anomaly & Issue Diagnostics
    {
        "name": "Total Issues Detected",
        "expression": "COUNTROWS(Fact_QualityIssues)",
        "formatString": "#,##0",
    },
    {
        "name": "Critical Issues",
        "expression": "CALCULATE(COUNTROWS(Fact_QualityIssues), Dim_Severity[severity_code] = \"CRITICAL\")",
        "formatString": "#,##0",
    },
    {
        "name": "Warning Issues",
        "expression": "CALCULATE(COUNTROWS(Fact_QualityIssues), Dim_Severity[severity_code] = \"WARNING\")",
        "formatString": "#,##0",
    },
    {
        "name": "Info Issues",
        "expression": "CALCULATE(COUNTROWS(Fact_QualityIssues), Dim_Severity[severity_code] = \"INFO\")",
        "formatString": "#,##0",
    },
    {
        "name": "Critical Issue Rate %",
        "expression": "DIVIDE([Critical Issues], [Total Issues Detected], 0)",
        "formatString": "0.0%",
    },
    {
        "name": "Total Defective Rows",
        "expression": "SUM(Fact_QualityIssues[affected_count])",
        "formatString": "#,##0",
    },

    # Category 4: Transformation Lineage & Cleaning ROI
    {
        "name": "Total Cleaning Jobs",
        "expression": "COUNTROWS(Fact_CleaningJobs)",
        "formatString": "#,##0",
    },
    {
        "name": "Total Rows Remediated",
        "expression": "SUM(Fact_CleaningJobs[rows_modified])",
        "formatString": "#,##0",
    },
    {
        "name": "Total Duplicates Removed",
        "expression": "SUM(Fact_CleaningJobs[rows_removed])",
        "formatString": "#,##0",
    },
    {
        "name": "Avg Quality Score Delta",
        "expression": "DIVIDE(AVERAGE(Fact_CleaningJobs[quality_score_delta]), 100, 0)",
        "formatString": "+0.0%;-0.0%;0.0%",
    },
    {
        "name": "Raw Quality Score",
        "expression": "CALCULATE([Avg Quality Score], Dim_Version[version_number] = 1)",
        "formatString": "0.0%",
    },
    {
        "name": "Cleaned Quality Score",
        "expression": "CALCULATE([Avg Quality Score], Dim_Version[version_number] > 1, Dim_Version[is_latest_version] = 1)",
        "formatString": "0.0%",
    },
    {
        "name": "Cleaning Net Lift %",
        "expression": "[Cleaned Quality Score] - [Raw Quality Score]",
        "formatString": "+0.0%;-0.0%;0.0%",
    },

    # Category 5: Dynamic Formatting & UI Badges
    {
        "name": "Grade Color Hex",
        "expression": [
            "VAR Score = [Latest Quality Score] * 100",
            "RETURN",
            "    SWITCH(",
            "        TRUE(),",
            "        Score >= 90.0, \"#10B981\",",
            "        Score >= 80.0, \"#38BDF8\",",
            "        Score >= 70.0, \"#F59E0B\",",
            "        Score >= 60.0, \"#F97316\",",
            "        \"#EF4444\"",
            "    )",
        ],
    },
    {
        "name": "Trust Status Badge",
        "expression": "IF([Latest Quality Score] >= 0.8, \"🟢 TRUSTED FOR PRODUCTION\", \"🔴 UNTRUSTED / NEEDS CLEANING\")",
    },
]

# Assign lineage tags
for m in measures_list:
    m["lineageTag"] = str(uuid.uuid4())

# Apply to _measures table
found_measures_table = False
for t in model["tables"]:
    if t["name"].lower() == "_measures":
        t["measures"] = measures_list
        found_measures_table = True
        break

if not found_measures_table:
    raise ValueError("Table '_measures' not found in model!")

# Encode updated DataModelSchema back to UTF-16LE
updated_schema_bytes = json.dumps(schema, ensure_ascii=False).encode("utf-16le")
file_map["DataModelSchema"] = updated_schema_bytes

# Remove old SecurityBindings so Power BI recalculates it cleanly on load
if "SecurityBindings" in file_map:
    del file_map["SecurityBindings"]

# Write updated pbix
with zipfile.ZipFile(pbix_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
    for fname, content in file_map.items():
        zout.writestr(fname, content)

print(f"✅ Successfully updated {pbix_path}!")
print(f"-> Active Star Schema relationships: 11")
print(f"-> Inactive Star Schema relationships: 1 (source_version_id for USERELATIONSHIP)")
print(f"-> Ingested DAX measures: {len(measures_list)}")
