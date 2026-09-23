"""Command-line runner for the DataProfiler engine.

Usage:
    python scripts/run_profiler.py [optional_path_to_csv_or_excel]
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path so 'src' is importable when executed directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.profiler import DataProfiler


def main():
    parser = argparse.ArgumentParser(description="Profile a dataset using DataProfiler.")
    parser.add_argument(
        "filepath",
        nargs="?",
        default="data/raw/netflix_titles.csv",
        help="Path to the dataset (CSV or Excel)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="data/sample/netflix_profile.json",
        help="Output path for the profile JSON file",
    )
    args = parser.parse_args()

    input_path = Path(args.filepath)
    if not input_path.exists():
        print(f"Error: File '{input_path}' does not exist.")
        sys.exit(1)

    print(f"\n[DataProfiler] Loading '{input_path}'...")
    if input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
    elif input_path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(input_path)
    else:
        print(f"Error: Unsupported file extension '{input_path.suffix}'. Use .csv or .xlsx.")
        sys.exit(1)

    profiler = DataProfiler()
    print("[DataProfiler] Analyzing structure and computing statistics...")
    profile = profiler.profile(df)

    # Display clean CLI overview
    summary = profile.summary
    print("\n" + "=" * 60)
    print(" DATASET PROFILE SUMMARY")
    print("=" * 60)
    print(f"  Rows:                 {summary.total_rows:,}")
    print(f"  Columns:              {summary.total_columns:,}")
    print(f"  Total Data Cells:     {summary.total_cells:,}")
    print(f"  Missing Cells:        {summary.total_missing_cells:,} ({summary.missing_percentage}%)")
    print(f"  Duplicate Rows:       {summary.duplicate_rows:,} ({summary.duplicate_percentage}%)")
    print(f"  Memory Footprint:     {summary.memory_bytes / (1024 * 1024):.2f} MB")
    print("\n  Column Type Breakdown:")
    for sem_type, count in summary.column_types_breakdown.items():
        print(f"    - {sem_type.capitalize()}: {count} columns")

    print("\n" + "=" * 60)
    print(" TOP MISSING VALUE COLUMNS")
    print("=" * 60)
    if profile.missing_rankings:
        for item in profile.missing_rankings[:5]:
            print(
                f"  - {item['column']:<20} | Missing: {item['null_count']:,} ({item['null_percentage']}%) | Type: {item['semantic_type']}"
            )
    else:
        print("  No missing values detected.")

    # Save to JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(profile.to_json(indent=2))

    print(f"\n[DataProfiler] Full profile exported successfully to: {output_path}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
