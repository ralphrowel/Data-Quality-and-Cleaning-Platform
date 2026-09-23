"""Tests for DatasetRepository and Hybrid Storage (Phase 6)."""

from pathlib import Path
import tempfile
import pandas as pd
import pytest

from src.cleaner import DataCleaningEngine
from src.quality import DataQualityEngine
from src.repository import DatasetRepository
from src.scorer import DataQualityScorer


@pytest.fixture
def temp_repo():
    """Provides an isolated test repository in a temporary directory."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = Path(tmp_dir) / "test_platform.db"
        storage_dir = Path(tmp_dir) / "storage"
        repo = DatasetRepository(db_path=db_path)
        yield repo, storage_dir


def test_dataset_creation(temp_repo):
    """Verify logical dataset registration."""
    repo, _ = temp_repo
    dataset = repo.create_dataset(
        name="Customer Churn",
        original_filename="churn_raw.csv",
        description="Telco customer records",
        user_id="user_123",
    )

    assert dataset.id is not None
    assert dataset.name == "Customer Churn"
    assert dataset.user_id == "user_123"

    retrieved = repo.get_dataset(dataset.id)
    assert retrieved is not None
    assert retrieved["name"] == "Customer Churn"


def test_version_lineage_and_parquet_persistence(temp_repo):
    """Verify creating version snapshots saves Parquet files and records metadata."""
    repo, storage_dir = temp_repo
    dataset = repo.create_dataset(name="Sales", original_filename="sales.csv")

    df_v1 = pd.DataFrame({"sale_id": [1, 2, 3], "amount": [100.5, 200.0, None]})
    v1 = repo.create_version(dataset.id, df_v1, storage_dir=storage_dir)

    assert v1.version_number == 1
    assert Path(v1.storage_path).exists()
    assert v1.row_count == 3
    assert v1.column_count == 2

    # Clean and create version 2
    cleaner = DataCleaningEngine()
    clean_result = cleaner.clean(df_v1, missing_strategies={"amount": {"strategy": "mean"}})
    v2 = repo.create_version(
        dataset.id,
        clean_result.cleaned_df,
        storage_dir=storage_dir,
        parent_version_id=v1.id,
    )

    assert v2.version_number == 2
    assert v2.parent_version_id == v1.id

    # Verify reloading from disk
    reloaded_df = repo.load_version_dataframe(v2.id)
    assert len(reloaded_df) == 3
    assert reloaded_df["amount"].isna().sum() == 0


def test_quality_report_persistence(temp_repo):
    """Verify saving quality scores and detected issues."""
    repo, storage_dir = temp_repo
    dataset = repo.create_dataset(name="Inventory", original_filename="inventory.csv")
    df = pd.DataFrame({"sku": ["A1", "A1", "B2"], "qty": [10, -5, None]})

    v1 = repo.create_version(dataset.id, df, storage_dir=storage_dir)

    quality_engine = DataQualityEngine()
    quality_report = quality_engine.analyze(df, id_columns=["sku"])

    scorer = DataQualityScorer()
    score_result = scorer.score(df, existing_report=quality_report)

    report_record = repo.save_quality_report(v1.id, score_result, quality_report)
    assert report_record.id is not None
    assert report_record.version_id == v1.id
    assert report_record.overall_score == score_result.overall_score

    # Check that versions query includes the quality scores
    versions = repo.get_dataset_versions(dataset.id)
    assert len(versions) == 1
    assert versions[0]["overall_score"] is not None
    assert versions[0]["grade"] is not None


def test_cleaning_job_audit_logging(temp_repo):
    """Verify logging a cleaning job connecting two dataset versions."""
    repo, storage_dir = temp_repo
    dataset = repo.create_dataset(name="Leads", original_filename="leads.csv")

    df_raw = pd.DataFrame({"email": ["a@b.com", "c@d.com", None]})
    v1 = repo.create_version(dataset.id, df_raw, storage_dir=storage_dir)

    cleaner = DataCleaningEngine()
    clean_result = cleaner.clean(df_raw, missing_strategies={"email": {"strategy": "drop"}})
    v2 = repo.create_version(dataset.id, clean_result.cleaned_df, storage_dir=storage_dir, parent_version_id=v1.id)

    job = repo.record_cleaning_job(v1.id, v2.id, clean_result, quality_score_delta=5.0)
    assert job.id is not None
    assert job.source_version_id == v1.id
    assert job.target_version_id == v2.id
    assert job.quality_score_delta == 5.0
    assert "drop_missing" in job.execution_log_json
