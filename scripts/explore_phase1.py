"""Phase 1: Data Understanding & Exploration Script.

Dataset: data/raw/netflix_titles.csv
Learning Milestones:
- V1.0: Dataset Loading & Fundamentals
- V1.1: Dataset Exploration (.shape, .info, .describe)
- V1.2: Missing-Value Diagnostics
- V1.3: Duplicate Detection
- V1.4: Data-Type Inspection & Parsing
- V1.5: Controlled Cleaning Practice
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

DATA_PATH = Path("data/raw/netflix_titles.csv")


def run_phase1():
    print("=" * 70)
    print(" PHASE 1: DATA UNDERSTANDING & EXPLORATION")
    print("=" * 70)

    # -------------------------------------------------------------
    # V1.0 — DATASET LOADING
    # -------------------------------------------------------------
    print("\n--- [V1.0] Loading Dataset ---")
    if not DATA_PATH.exists():
        print(f"Error: {DATA_PATH} not found!")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    print(f"Successfully loaded {DATA_PATH.name}")
    print(f"Rows (observations): {df.shape[0]:,}")
    print(f"Columns (attributes): {df.shape[1]}")
    print(f"Index range: {df.index.start} to {df.index.stop - 1}")

    # -------------------------------------------------------------
    # V1.1 — DATASET EXPLORATION
    # -------------------------------------------------------------
    print("\n--- [V1.1] Dataset Exploration ---")
    print("\nColumns list:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col:<20} | Type: {df[col].dtype}")

    print("\nSummary Statistics for Numeric Columns:")
    print(df.describe().T[["count", "mean", "std", "min", "50%", "max"]])

    print("\nCategorical Value Distribution for 'type':")
    print(df["type"].value_counts(dropna=False))

    # -------------------------------------------------------------
    # V1.2 — MISSING DATA DIAGNOSTICS
    # -------------------------------------------------------------
    print("\n--- [V1.2] Missing-Value Analysis ---")
    total_cells = df.size
    total_missing = df.isna().sum().sum()
    print(f"Total dataset cells: {total_cells:,}")
    print(f"Total missing cells: {total_missing:,} ({(total_missing / total_cells) * 100:.2f}%)")

    missing_series = df.isna().sum()
    missing_pct = (missing_series / len(df)) * 100
    missing_report = (
        pd.DataFrame({"missing_count": missing_series, "missing_percent": missing_pct})
        .query("missing_count > 0")
        .sort_values(by="missing_count", ascending=False)
    )
    print("\nColumns with Missing Values:")
    print(missing_report.to_string())

    # -------------------------------------------------------------
    # V1.3 — DUPLICATE DETECTION
    # -------------------------------------------------------------
    print("\n--- [V1.3] Duplicate Analysis ---")
    exact_duplicates = df.duplicated().sum()
    id_duplicates = df.duplicated(subset=["show_id"]).sum()
    title_type_duplicates = df.duplicated(subset=["title", "type"]).sum()
    print(f"Exact duplicate rows: {exact_duplicates}")
    print(f"Duplicate 'show_id' keys: {id_duplicates}")
    print(f"Duplicate ('title', 'type') pairs: {title_type_duplicates}")

    if title_type_duplicates > 0:
        dup_titles = df[df.duplicated(subset=["title", "type"], keep=False)].sort_values(by="title")
        print("\nSample title duplicates found:")
        print(dup_titles[["show_id", "type", "title", "release_year"]].head(6))

    # -------------------------------------------------------------
    # V1.4 — DATA TYPES & ANOMALIES
    # -------------------------------------------------------------
    print("\n--- [V1.4] Data Types & Value Inspection ---")
    print(f"'date_added' raw dtype: {df['date_added'].dtype}")
    print(f"Sample 'date_added' raw values: {df['date_added'].dropna().head(3).tolist()}")

    # Check for leading/trailing whitespaces in string columns
    str_cols = df.select_dtypes(include=["object", "str"]).columns
    whitespace_issues = {}
    for col in str_cols:
        stripped = df[col].astype(str).str.strip()
        diff_count = (df[col].astype(str) != stripped).sum()
        if diff_count > 0:
            whitespace_issues[col] = diff_count

    print("\nColumns with Whitespace Padding:")
    if whitespace_issues:
        for col, count in whitespace_issues.items():
            print(f"  - {col}: {count:,} rows contain leading/trailing whitespaces")
    else:
        print("  None detected.")

    # -------------------------------------------------------------
    # V1.5 — CONTROLLED CLEANING PRACTICE
    # -------------------------------------------------------------
    print("\n--- [V1.5] Controlled Cleaning Simulation ---")
    clean_df = df.copy()

    # Step 1: Strip whitespaces across text columns
    for col in str_cols:
        clean_df[col] = clean_df[col].astype(str).str.strip()
        # restore 'nan' string back to real NaN
        clean_df[col] = clean_df[col].replace("nan", np.nan)

    # Step 2: Impute known missing categoricals
    clean_df["director"] = clean_df["director"].fillna("Unknown Director")
    clean_df["country"] = clean_df["country"].fillna("Unknown Country")
    clean_df["cast"] = clean_df["cast"].fillna("Unknown Cast")

    # Step 3: Parse dates
    clean_df["date_added"] = pd.to_datetime(clean_df["date_added"], format="mixed", errors="coerce")

    # Step 4: Verify results
    remaining_missing = clean_df.isna().sum()
    print("Missing values after controlled cleaning:")
    print(remaining_missing[remaining_missing > 0])

    print("\nCleaned DataFrame data types:")
    print(clean_df.dtypes[["show_id", "type", "title", "director", "date_added", "release_year"]])

    print("\n" + "=" * 70)
    print(" PHASE 1 COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_phase1()
