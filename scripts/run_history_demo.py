"""End-to-end demonstration of Phase 6: Dataset History & Hybrid Storage Lineage.

Usage:
    python scripts/run_history_demo.py
"""

from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.cleaner import DataCleaningEngine
from src.quality import DataQualityEngine
from src.repository import DatasetRepository
from src.scorer import DataQualityScorer


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    raw_path = Path("data/raw/netflix_titles.csv")
    if not raw_path.exists():
        print(f"Error: {raw_path} not found.")
        sys.exit(1)

    print("\n" + "=" * 70)
    print(" PHASE 6: DATASET HISTORY & HYBRID STORAGE LINEAGE DEMO")
    print("=" * 70)

    # 1. Initialize Repository
    repo = DatasetRepository(db_path="data/platform.db")
    print("\n[1/5] Initialized Relational Database: data/platform.db")

    # 2. Register Dataset
    dataset = repo.create_dataset(
        name="Netflix Movies & TV Shows",
        original_filename=raw_path.name,
        description="Global catalog of movies and television shows on Netflix.",
        user_id="analyst_alpha",
    )
    print(f"[2/5] Registered Dataset: '{dataset.name}' (ID: {dataset.id[:8]}...)")

    # 3. Create Version 1 (Raw)
    raw_df = pd.read_csv(raw_path)
    v1 = repo.create_version(dataset.id, raw_df, storage_dir="data/storage")
    print(f"      Created Version {v1.version_number} (Parquet snapshot: {Path(v1.storage_path).name})")

    # Evaluate Version 1 Quality
    quality_engine = DataQualityEngine()
    scorer = DataQualityScorer()

    v1_report = quality_engine.analyze(raw_df, id_columns=["show_id"])
    v1_score = scorer.score(raw_df, id_columns=["show_id"], existing_report=v1_report)
    repo.save_quality_report(v1.id, v1_score, v1_report)
    print(f"      Version {v1.version_number} Quality Score: {v1_score.overall_score:.1f}% (Grade {v1_score.grade})")

    # 4. Clean and Create Version 2
    print("\n[3/5] Executing Data Cleaning Pipeline...")
    cleaner = DataCleaningEngine()
    clean_result = cleaner.clean(
        raw_df,
        strip_whitespace=True,
        normalize_column_names=True,
        date_columns=["date_added"],
        missing_strategies={
            "director": {"strategy": "constant", "value": "Unknown Director"},
            "country": {"strategy": "constant", "value": "Unknown Country"},
            "cast": {"strategy": "constant", "value": "Unknown Cast"},
            "rating": {"strategy": "mode"},
        },
        drop_duplicates_subset=["show_id"],
    )

    v2 = repo.create_version(
        dataset.id,
        clean_result.cleaned_df,
        storage_dir="data/storage",
        parent_version_id=v1.id,
    )
    print(f"      Created Version {v2.version_number} (Parquet snapshot: {Path(v2.storage_path).name})")

    # Evaluate Version 2 Quality
    v2_report = quality_engine.analyze(clean_result.cleaned_df, id_columns=["show_id"])
    v2_score = scorer.score(clean_result.cleaned_df, id_columns=["show_id"], existing_report=v2_report)
    repo.save_quality_report(v2.id, v2_score, v2_report)
    print(f"      Version {v2.version_number} Quality Score: {v2_score.overall_score:.1f}% (Grade {v2_score.grade})")

    # 5. Record Lineage Transformation Job
    score_delta = round(v2_score.overall_score - v1_score.overall_score, 2)
    job = repo.record_cleaning_job(v1.id, v2.id, clean_result, quality_score_delta=score_delta)
    print(f"\n[4/5] Recorded Cleaning Job (ID: {job.id[:8]}... | Delta: +{score_delta:.2f}%)")

    # 6. Query Version History Table
    print("\n[5/5] Querying Stored Dataset History & Lineage:")
    print("=" * 70)
    versions = repo.get_dataset_versions(dataset.id)
    print(f"{'Ver':<5} | {'Rows':<8} | {'Columns':<8} | {'Overall Score':<14} | {'Grade':<6} | {'Completeness':<13} | {'Parquet File'}")
    print("-" * 70)
    for v in versions:
        fname = Path(v['storage_path']).name
        print(
            f"V{v['version_number']:<4} | {v['row_count']:<8,} | {v['column_count']:<8} | {v['overall_score']:>6.1f}%       | {v['grade']:<6} | {v['completeness_score']:>6.1f}%       | {fname}"
        )
    print("=" * 70)
    print("Dataset lineage, quality audit records, and Parquet snapshots preserved.\n")


if __name__ == "__main__":
    main()
