"""Command-line runner for the DataCleaningEngine.

Usage:
    python scripts/run_cleaner.py [optional_path_to_csv_or_excel]
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.cleaner import DataCleaningEngine


def main():
    parser = argparse.ArgumentParser(description="Clean a dataset using DataCleaningEngine.")
    parser.add_argument(
        "filepath",
        nargs="?",
        default="data/raw/netflix_titles.csv",
        help="Path to the raw dataset (CSV or Excel)",
    )
    args = parser.parse_args()

    input_path = Path(args.filepath)
    if not input_path.exists():
        print(f"Error: File '{input_path}' does not exist.")
        sys.exit(1)

    print(f"\n[DataCleaningEngine] Loading '{input_path}'...")
    df = pd.read_csv(input_path)

    cleaner = DataCleaningEngine()
    print("[DataCleaningEngine] Executing deterministic transformation pipeline...")

    # Configure realistic cleaning operations for the netflix dataset
    result = cleaner.clean(
        df,
        strip_whitespace=True,
        normalize_column_names=True,
        date_columns=["date_added"] if "date_added" in df.columns else None,
        missing_strategies={
            "director": {"strategy": "constant", "value": "Unknown Director"},
            "country": {"strategy": "constant", "value": "Unknown Country"},
            "cast": {"strategy": "constant", "value": "Unknown Cast"},
            "rating": {"strategy": "mode"},
        },
        drop_duplicates_subset=["show_id"] if "show_id" in df.columns else True,
    )

    # Configure UTF-8 stdout if available
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    # Console display of before and after
    b = result.before_stats
    a = result.after_stats
    d = result.delta

    print("\n" + "=" * 65)
    print(" DATA CLEANING EXECUTION SUMMARY")
    print("=" * 65)
    print(f"  Total Operations Executed:  {d['total_operations']}")
    print(f"  Rows Before / After:        {b['total_rows']:,} -> {a['total_rows']:,} (Delta: {d['rows_removed']:,})")
    print(f"  Missing Cells:              {b['missing_cells']:,} -> {a['missing_cells']:,} (Resolved: {d['missing_cells_resolved']:,})")
    print(f"  Missing Cell Percentage:    {b['missing_percentage']}% -> {a['missing_percentage']}%")
    print(f"  Duplicate Rows:             {b['duplicate_rows']:,} -> {a['duplicate_rows']:,}")

    print("\n" + "=" * 65)
    print(" AUDIT LOG: EXECUTED PIPELINE STEPS")
    print("=" * 65)
    for step in result.steps:
        target = f"[{step.target_column}]" if step.target_column else "[Dataset-Level]"
        print(f"  Step {step.step_number}. {target:<20} {step.details}")

    # Export versions
    parquet_path = Path("data/sample/netflix_cleaned.parquet")
    csv_path = Path("data/sample/netflix_cleaned.csv")
    log_path = Path("data/sample/netflix_cleaning_log.json")

    result.export_parquet(parquet_path)
    result.export_safe_csv(csv_path)

    with open(log_path, "w", encoding="utf-8") as f:
        f.write(result.to_json(indent=2))

    print("\n" + "=" * 65)
    print(" EXPORTED ARTIFACTS")
    print("=" * 65)
    print(f"  - Internal Schema-Safe Snapshot: {parquet_path} ({parquet_path.stat().st_size / (1024 * 1024):.2f} MB)")
    print(f"  - Safe CSV (Formula Sanitized):  {csv_path} ({csv_path.stat().st_size / (1024 * 1024):.2f} MB)")
    print(f"  - Auditable Transformation Log:  {log_path}")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
