"""End-to-End Integration Workflow Tests (Phase 10 — V10.3).

Verifies the complete platform lifecycle sequentially:
Raw Dataset Ingestion
    ↓
Data Profiling (V2)
    ↓
Data Quality Checks (V3)
    ↓
Quality Scoring & Grading (V5)
    ↓
Relational Persistence & V1 Snapshot (V6)
    ↓
Deterministic Cleaning Pipeline (V4)
    ↓
V2 Parquet Snapshot & Cleaning Job Lineage Audit (V6)
    ↓
Post-Cleaning Re-Scoring & Quality Delta Verification
    ↓
Sanitized CSV Export with Formula Injection Defense (V11)
"""

from pathlib import Path
import tempfile
import pandas as pd
import pytest

from src.cleaner import DataCleaningEngine
from src.profiler import DataProfiler
from src.quality import DataQualityEngine
from src.repository import DatasetRepository
from src.scorer import DataQualityScorer


def test_full_lifecycle_workflow():
    """Verify complete end-to-end data pipeline from raw ingestion to sanitized export."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "lifecycle_platform.db"
        storage_dir = Path(tmp_dir) / "storage"
        export_dir = Path(tmp_dir) / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        repo = DatasetRepository(db_path=db_path)

        # 1. Raw Dataset with intentional defects
        raw_data = {
            "ID": [101, 102, 103, 104, 104],  # duplicate key and duplicate row
            " Full Name ": ["  Alice Smith ", "Bob Jones", "Charlie Brown ", "Dana White", "Dana White"],
            "Email": ["alice@corp.com", "bob@corp.com", None, "dana@corp.com", "dana@corp.com"],
            "Salary": [85000, 92000, -5000, 75000, 75000],  # negative invalid salary
            "Status": ["active", "ACTIVE", "Active", "Pending", "Pending"],
            "Notes": ["=SUM(A1:A10)", "None", "Regular employee", "Contractor", "Contractor"],  # Formula trigger
        }
        df_raw = pd.DataFrame(raw_data)

        # 2. Step 1: Profiling
        profiler = DataProfiler()
        profile_res = profiler.profile(df_raw)
        assert profile_res.summary.total_rows == 5
        assert profile_res.summary.total_columns == 6
        assert profile_res.summary.duplicate_rows >= 1
        assert len(profile_res.missing_rankings) >= 1

        # 3. Step 2: Quality Analysis
        quality_engine = DataQualityEngine()
        quality_rep = quality_engine.analyze(
            df_raw,
            id_columns=["ID"],
            format_rules={"Email": "email"},
            range_rules={"Salary": {"min": 0, "max": 500000}},
        )
        assert len(quality_rep.issues) >= 3

        # 4. Step 3: Baseline Quality Scoring
        scorer = DataQualityScorer()
        raw_score = scorer.score(
            df_raw,
            id_columns=["ID"],
            format_rules={"Email": "email"},
            range_rules={"Salary": {"min": 0, "max": 500000}},
        )
        assert raw_score.overall_score < 100.0
        assert raw_score.grade in ["B", "C", "D", "F"]

        # 5. Step 4: Relational Dataset & Version 1 Registration
        dataset = repo.create_dataset(
            name="Employee Registry",
            original_filename="employees_raw.csv",
            description="Q3 Payroll and personnel audit",
        )
        v1 = repo.create_version(
            dataset_id=dataset.id,
            df=df_raw,
            storage_dir=storage_dir,
        )
        assert v1.version_number == 1
        assert Path(v1.storage_path).exists()

        # Save baseline quality report
        repo.save_quality_report(
            version_id=v1.id,
            score_result=raw_score,
            quality_report=quality_rep,
        )

        # 6. Step 5: Deterministic Cleaning Execution
        cleaner = DataCleaningEngine()
        clean_res = cleaner.clean(
            df_raw,
            strip_whitespace=True,
            normalize_column_names=True,
            drop_duplicates_subset=True,
            missing_strategies={"Email": {"strategy": "constant", "value": "unassigned@corp.com"}},
            casing_rules={"Status": "title"},
        )
        df_cleaned = clean_res.cleaned_df

        assert len(clean_res.steps) >= 3
        assert clean_res.delta.get("rows_removed", 0) >= 1  # Duplicate dropped

        # 7. Step 6: Post-Cleaning Scoring & Delta Calculation
        cleaned_score = scorer.score(
            df_cleaned,
            id_columns=["ID"],
            format_rules={"Email": "email"},
        )
        assert cleaned_score.overall_score > raw_score.overall_score
        score_delta = round(cleaned_score.overall_score - raw_score.overall_score, 2)
        assert score_delta > 0.0

        # 8. Step 7: Record Version 2 & Cleaning Job Audit Trail
        v2 = repo.create_version(
            dataset_id=dataset.id,
            df=df_cleaned,
            storage_dir=storage_dir,
            parent_version_id=v1.id,
        )
        assert v2.version_number == 2
        assert v2.parent_version_id == v1.id
        assert Path(v2.storage_path).exists()

        job = repo.record_cleaning_job(
            source_version_id=v1.id,
            target_version_id=v2.id,
            cleaning_result=clean_res,
            quality_score_delta=score_delta,
        )
        assert job.id is not None


        # 9. Step 8: Sanitized CSV Export Verification
        export_file = export_dir / "employees_cleaned.csv"
        clean_res.export_safe_csv(export_file)

        assert export_file.exists()
        content = export_file.read_text(encoding="utf-8")
        assert "'=SUM(A1:A10)" in content  # Neutralized
        assert "\n=SUM" not in content     # No active executable formulas

