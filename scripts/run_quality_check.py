"""Command-line runner for the DataQualityEngine.

Usage:
    python scripts/run_quality_check.py [optional_path_to_csv_or_excel]
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.quality import DataQualityEngine


def main():
    parser = argparse.ArgumentParser(description="Run data quality checks using DataQualityEngine.")
    parser.add_argument(
        "filepath",
        nargs="?",
        default="data/raw/netflix_titles.csv",
        help="Path to the dataset (CSV or Excel)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/sample/netflix_quality_report.json",
        help="Output path for the quality report JSON",
    )
    args = parser.parse_args()

    input_path = Path(args.filepath)
    if not input_path.exists():
        print(f"Error: File '{input_path}' does not exist.")
        sys.exit(1)

    print(f"\n[DataQualityEngine] Loading '{input_path}'...")
    if input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    elif input_path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(input_path)
    else:
        print(f"Error: Unsupported file extension '{input_path.suffix}'.")
        sys.exit(1)

    engine = DataQualityEngine()
    print("[DataQualityEngine] Executing multi-dimensional quality diagnostics...")

    # Configure dataset-specific rule parameters if analyzing netflix dataset
    id_cols = ["show_id"] if "show_id" in df.columns else None
    range_rules = {"release_year": {"min": 1900, "max": 2026}} if "release_year" in df.columns else None
    cat_rules = {"type": ["Movie", "TV Show"]} if "type" in df.columns else None

    report = engine.analyze(
        df,
        id_columns=id_cols,
        range_rules=range_rules,
        category_rules=cat_rules,
    )

    # CLI Output
    print("\n" + "=" * 65)
    print(" DATA QUALITY ISSUE REPORT")
    print("=" * 65)
    print(f"  Total Rows:                 {report.total_rows:,}")
    print(f"  Total Columns:              {report.total_columns:,}")
    print(f"  Total Defect Occurrences:   {report.total_issues_count:,}")

    print("\n  Issues by Category:")
    for cat, count in report.issues_by_category.items():
        print(f"    - {cat:<24} : {count:,} affected values")

    print("\n  Issues by Severity:")
    for sev, count in report.issues_by_severity.items():
        print(f"    - {sev:<10} : {count:,}")

    print("\n" + "=" * 65)
    print(" DETECTED QUALITY ISSUES DETAIL")
    print("=" * 65)
    for issue in report.issues:
        col_str = f"[{issue.column}]" if issue.column else "[Row-Level]"
        print(f"  [{issue.severity.value:<8}] {col_str:<22} {issue.description}")

    # Export JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report.to_json(indent=2))

    print(f"\n[DataQualityEngine] Full report exported to: {output_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
