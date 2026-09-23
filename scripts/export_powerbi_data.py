"""Power BI Data Export & ETL Script.

Phase 9: V9.0 – V9.7
Extracts relational platform metadata, quality scores, issue logs, and cleaning lineage
from the SQLite/PostgreSQL database and formats them into a clean, optimized Star Schema
ready for direct import into Power BI Desktop.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def export_powerbi_star_schema(db_path: str = "data/platform.db", output_dir: str = "powerbi/data"):
    """Extracts tables, denormalizes dimensions, and outputs Star Schema CSVs for Power BI."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Connecting to database: {db_path}...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # 1. Dim_Dataset
    datasets_df = pd.read_sql_query(
        """
        SELECT
            id AS dataset_id,
            name AS dataset_name,
            original_filename,
            CASE
                WHEN LOWER(original_filename) LIKE '%.csv' THEN 'CSV'
                WHEN LOWER(original_filename) LIKE '%.xlsx' OR LOWER(original_filename) LIKE '%.xls' THEN 'Excel'
                ELSE 'Other'
            END AS file_format_type,
            user_id,
            created_at,
            updated_at
        FROM datasets
        ORDER BY created_at ASC
        """,
        conn,
    )
    datasets_df.to_csv(output_path / "Dim_Dataset.csv", index=False)
    print(f"-> Exported Dim_Dataset: {len(datasets_df)} rows")

    # 2. Dim_Version
    versions_df = pd.read_sql_query(
        """
        WITH latest_versions AS (
            SELECT dataset_id, MAX(version_number) AS max_v
            FROM dataset_versions
            GROUP BY dataset_id
        )
        SELECT
            v.id AS version_id,
            v.dataset_id,
            v.version_number,
            'v' || v.version_number || CASE WHEN v.version_number = 1 THEN ' (Raw)' ELSE ' (Cleaned)' END AS version_label,
            v.parent_version_id,
            v.file_format,
            v.row_count,
            v.column_count,
            v.file_size_bytes,
            ROUND(v.file_size_bytes / 1024.0 / 1024.0, 3) AS file_size_mb,
            CASE WHEN v.version_number = lv.max_v THEN 1 ELSE 0 END AS is_latest_version,
            v.created_at
        FROM dataset_versions v
        LEFT JOIN latest_versions lv ON v.dataset_id = lv.dataset_id
        ORDER BY v.dataset_id, v.version_number ASC
        """,
        conn,
    )
    versions_df.to_csv(output_path / "Dim_Version.csv", index=False)
    print(f"-> Exported Dim_Version: {len(versions_df)} rows")

    # 3. Dim_Severity
    severity_data = [
        {"severity_code": "CRITICAL", "severity_name": "Critical", "severity_weight": 3, "color_hex": "#EF4444"},
        {"severity_code": "WARNING", "severity_name": "Warning", "severity_weight": 2, "color_hex": "#F59E0B"},
        {"severity_code": "INFO", "severity_name": "Informational", "severity_weight": 1, "color_hex": "#38BDF8"},
    ]
    pd.DataFrame(severity_data).to_csv(output_path / "Dim_Severity.csv", index=False)
    print("-> Exported Dim_Severity: 3 rows")

    # 4. Dim_Grade
    grade_data = [
        {"grade": "A", "grade_name": "Grade A (Excellent)", "min_score": 90.0, "max_score": 100.0, "is_trustworthy": 1, "color_hex": "#10B981"},
        {"grade": "B", "grade_name": "Grade B (Good)", "min_score": 80.0, "max_score": 89.9, "is_trustworthy": 1, "color_hex": "#38BDF8"},
        {"grade": "C", "grade_name": "Grade C (Caution)", "min_score": 70.0, "max_score": 79.9, "is_trustworthy": 0, "color_hex": "#F59E0B"},
        {"grade": "D", "grade_name": "Grade D (Poor)", "min_score": 60.0, "max_score": 69.9, "is_trustworthy": 0, "color_hex": "#F97316"},
        {"grade": "F", "grade_name": "Grade F (Untrusted)", "min_score": 0.0, "max_score": 59.9, "is_trustworthy": 0, "color_hex": "#EF4444"},
    ]
    pd.DataFrame(grade_data).to_csv(output_path / "Dim_Grade.csv", index=False)
    print("-> Exported Dim_Grade: 5 rows")

    # 5. Dim_Date (Dynamic Calendar generation based on metadata dates)
    dates_df = pd.read_sql_query(
        """
        SELECT created_at FROM datasets
        UNION
        SELECT created_at FROM dataset_versions
        UNION
        SELECT created_at FROM quality_reports
        """,
        conn,
    )
    if not dates_df.empty:
        dates_df["dt"] = pd.to_datetime(dates_df["created_at"], errors="coerce")
        min_date = dates_df["dt"].min().floor("D")
        max_date = dates_df["dt"].max().ceil("D")
    else:
        min_date = datetime.now(timezone.utc).floor("D")
        max_date = min_date

    # Pad with 30 days before and after for smooth visual date ranges
    date_range = pd.date_range(start=min_date - pd.Timedelta(days=14), end=max_date + pd.Timedelta(days=14), freq="D")
    dim_date = pd.DataFrame({"FullDate": date_range})
    dim_date["DateKey"] = dim_date["FullDate"].dt.strftime("%Y%m%d").astype(int)
    dim_date["Year"] = dim_date["FullDate"].dt.year
    dim_date["Quarter"] = "Q" + dim_date["FullDate"].dt.quarter.astype(str)
    dim_date["YearQuarter"] = dim_date["Year"].astype(str) + "-Q" + dim_date["FullDate"].dt.quarter.astype(str)
    dim_date["MonthNumber"] = dim_date["FullDate"].dt.month
    dim_date["MonthName"] = dim_date["FullDate"].dt.strftime("%B")
    dim_date["MonthShort"] = dim_date["FullDate"].dt.strftime("%b")
    dim_date["YearMonth"] = dim_date["FullDate"].dt.strftime("%Y-%m")
    dim_date["DayOfMonth"] = dim_date["FullDate"].dt.day
    dim_date["DayOfWeek"] = dim_date["FullDate"].dt.day_name()
    dim_date["IsWeekend"] = dim_date["FullDate"].dt.weekday.isin([5, 6]).astype(int)

    dim_date.to_csv(output_path / "Dim_Date.csv", index=False)
    print(f"-> Exported Dim_Date: {len(dim_date)} rows")

    # 6. Fact_QualityEvaluation (Grain: One row per quality report evaluated)
    fact_eval = pd.read_sql_query(
        """
        SELECT
            qr.id AS report_id,
            qr.version_id,
            v.dataset_id,
            strftime('%Y%m%d', qr.created_at) AS date_key,
            qr.created_at,
            qr.overall_score,
            qr.grade,
            qr.completeness_score,
            qr.validity_score,
            qr.uniqueness_score,
            qr.consistency_score,
            CASE WHEN qr.is_trustworthy = 1 OR qr.overall_score >= 80.0 THEN 1 ELSE 0 END AS is_trustworthy,
            v.row_count,
            v.column_count,
            v.file_size_bytes
        FROM quality_reports qr
        JOIN dataset_versions v ON qr.version_id = v.id
        ORDER BY qr.created_at ASC
        """,
        conn,
    )
    fact_eval.to_csv(output_path / "Fact_QualityEvaluation.csv", index=False)
    print(f"-> Exported Fact_QualityEvaluation: {len(fact_eval)} rows")

    # 7. Fact_QualityIssues (Grain: One row per detected defect)
    fact_issues = pd.read_sql_query(
        """
        SELECT
            qi.id AS issue_id,
            qi.report_id,
            qr.version_id,
            v.dataset_id,
            strftime('%Y%m%d', qi.created_at) AS date_key,
            qi.created_at,
            UPPER(qi.category) AS issue_category,
            UPPER(qi.severity) AS severity_code,
            COALESCE(qi.column_name, '(Dataset Level)') AS column_name,
            qi.description,
            qi.affected_count,
            qi.affected_percentage,
            CASE
                WHEN UPPER(qi.severity) = 'CRITICAL' THEN 3
                WHEN UPPER(qi.severity) = 'WARNING' THEN 2
                ELSE 1
            END AS severity_weight
        FROM quality_issues qi
        JOIN quality_reports qr ON qi.report_id = qr.id
        JOIN dataset_versions v ON qr.version_id = v.id
        ORDER BY qi.created_at ASC
        """,
        conn,
    )
    fact_issues.to_csv(output_path / "Fact_QualityIssues.csv", index=False)
    print(f"-> Exported Fact_QualityIssues: {len(fact_issues)} rows")

    # 8. Fact_CleaningJobs (Grain: One row per cleaning pipeline run)
    fact_cleaning = pd.read_sql_query(
        """
        SELECT
            cj.id AS cleaning_job_id,
            cj.source_version_id,
            cj.target_version_id,
            v_target.dataset_id,
            strftime('%Y%m%d', cj.created_at) AS date_key,
            cj.created_at,
            cj.total_operations,
            cj.rows_modified,
            cj.quality_score_delta,
            v_src.row_count AS source_row_count,
            v_target.row_count AS target_row_count,
            (v_src.row_count - v_target.row_count) AS rows_removed,
            qr_src.overall_score AS source_score,
            qr_target.overall_score AS target_score
        FROM cleaning_jobs cj
        JOIN dataset_versions v_src ON cj.source_version_id = v_src.id
        JOIN dataset_versions v_target ON cj.target_version_id = v_target.id
        LEFT JOIN quality_reports qr_src ON v_src.id = qr_src.version_id
        LEFT JOIN quality_reports qr_target ON v_target.id = qr_target.version_id
        ORDER BY cj.created_at ASC
        """,
        conn,
    )
    fact_cleaning.to_csv(output_path / "Fact_CleaningJobs.csv", index=False)
    print(f"-> Exported Fact_CleaningJobs: {len(fact_cleaning)} rows")

    # 9. Denormalized Flat Table for Quick 1-Click Power BI Analysis
    flat_sql = """
        SELECT
            d.id AS dataset_id,
            d.name AS dataset_name,
            d.original_filename,
            v.id AS version_id,
            v.version_number,
            'v' || v.version_number AS version_label,
            qr.id AS report_id,
            qr.created_at AS evaluated_at,
            qr.overall_score,
            qr.grade,
            qr.completeness_score,
            qr.validity_score,
            qr.uniqueness_score,
            qr.consistency_score,
            qr.is_trustworthy,
            v.row_count,
            v.column_count,
            ROUND(v.file_size_bytes / 1024.0 / 1024.0, 2) AS file_size_mb
        FROM datasets d
        JOIN dataset_versions v ON d.id = v.dataset_id
        JOIN quality_reports qr ON v.id = qr.version_id
        ORDER BY d.created_at DESC, v.version_number ASC
    """
    flat_df = pd.read_sql_query(flat_sql, conn)
    flat_df.to_csv(output_path / "Platform_Quality_Analytics_Flat.csv", index=False)
    print(f"-> Exported Platform_Quality_Analytics_Flat: {len(flat_df)} rows")

    conn.close()
    print("\n✅ Power BI Star Schema data export complete! All files saved in 'powerbi/data/'.")


if __name__ == "__main__":
    export_powerbi_star_schema()
