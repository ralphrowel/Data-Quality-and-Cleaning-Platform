"""Database Repository Layer for Dataset History & Lineage.

Phase 6: V6.0 – V6.5
Implements the Hybrid Storage Model:
- Relational metadata, version lineage, and quality audit trails stored in DB
- Tabular data snapshots stored in Apache Parquet format on disk
"""

from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
import pandas as pd

from src.cleaner import CleaningResult
from src.models import (
    CleaningJobRecord,
    Dataset,
    DatasetVersion,
    QualityIssueRecord,
    QualityReportRecord,
    generate_uuid,
)
from src.quality import QualityReport
from src.scorer import QualityScoreResult


class DatasetRepository:
    """Manages relational persistence of dataset metadata, versions, and quality logs."""

    def __init__(self, db_path: str | Path = "data/platform.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connection(self):
        """Context manager guaranteeing connection commit and close."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes relational tables conforming to the Phase 6 schema."""
        with self._connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    original_filename TEXT NOT NULL,
                    user_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dataset_versions (
                    id TEXT PRIMARY KEY,
                    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
                    version_number INTEGER NOT NULL,
                    parent_version_id TEXT REFERENCES dataset_versions(id) ON DELETE SET NULL,
                    storage_path TEXT NOT NULL,
                    file_format TEXT NOT NULL DEFAULT 'parquet',
                    row_count INTEGER NOT NULL,
                    column_count INTEGER NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(dataset_id, version_number)
                );

                CREATE TABLE IF NOT EXISTS quality_reports (
                    id TEXT PRIMARY KEY,
                    version_id TEXT NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
                    overall_score REAL NOT NULL,
                    grade TEXT NOT NULL,
                    grade_label TEXT NOT NULL,
                    completeness_score REAL NOT NULL,
                    validity_score REAL NOT NULL,
                    uniqueness_score REAL NOT NULL,
                    consistency_score REAL NOT NULL,
                    is_trustworthy INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(version_id)
                );

                CREATE TABLE IF NOT EXISTS quality_issues (
                    id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL REFERENCES quality_reports(id) ON DELETE CASCADE,
                    category TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    column_name TEXT,
                    description TEXT NOT NULL,
                    affected_count INTEGER NOT NULL DEFAULT 0,
                    affected_percentage REAL NOT NULL DEFAULT 0.0,
                    suggested_action TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cleaning_jobs (
                    id TEXT PRIMARY KEY,
                    source_version_id TEXT NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
                    target_version_id TEXT NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
                    total_operations INTEGER NOT NULL DEFAULT 0,
                    rows_modified INTEGER NOT NULL DEFAULT 0,
                    quality_score_delta REAL NOT NULL DEFAULT 0.0,
                    execution_log_json TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def create_dataset(
        self,
        name: str,
        original_filename: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Dataset:
        """Registers a new logical dataset."""
        dataset = Dataset(
            name=name,
            original_filename=original_filename,
            description=description,
            user_id=user_id,
        )
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO datasets (id, name, description, original_filename, user_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset.id,
                    dataset.name,
                    dataset.description,
                    dataset.original_filename,
                    dataset.user_id,
                    dataset.created_at,
                    dataset.updated_at,
                ),
            )
        return dataset

    def create_version(
        self,
        dataset_id: str,
        df: pd.DataFrame,
        storage_dir: str | Path = "data/storage",
        parent_version_id: Optional[str] = None,
    ) -> DatasetVersion:
        """Saves a DataFrame to Parquet storage and records the immutable version snapshot."""
        storage_path = Path(storage_dir)
        storage_path.mkdir(parents=True, exist_ok=True)

        with self._connection() as conn:
            # Determine next version number
            cursor = conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) + 1 FROM dataset_versions WHERE dataset_id = ?",
                (dataset_id,),
            )
            next_version_num = cursor.fetchone()[0]

            # Generate unique internal parquet filename
            version_id = generate_uuid()
            parquet_filename = f"ds_{dataset_id[:8]}_v{next_version_num}_{version_id[:8]}.parquet"
            file_disk_path = storage_path / parquet_filename

            # Save DataFrame to Parquet
            df.to_parquet(file_disk_path, index=False, engine="pyarrow")
            file_size = file_disk_path.stat().st_size

            version = DatasetVersion(
                id=version_id,
                dataset_id=dataset_id,
                version_number=next_version_num,
                parent_version_id=parent_version_id,
                storage_path=str(file_disk_path),
                file_format="parquet",
                row_count=len(df),
                column_count=len(df.columns),
                file_size_bytes=file_size,
            )

            conn.execute(
                """
                INSERT INTO dataset_versions (id, dataset_id, version_number, parent_version_id,
                                              storage_path, file_format, row_count, column_count,
                                              file_size_bytes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version.id,
                    version.dataset_id,
                    version.version_number,
                    version.parent_version_id,
                    version.storage_path,
                    version.file_format,
                    version.row_count,
                    version.column_count,
                    version.file_size_bytes,
                    version.created_at,
                ),
            )

        return version

    def save_quality_report(
        self,
        version_id: str,
        score_result: QualityScoreResult,
        quality_report: Optional[QualityReport] = None,
    ) -> QualityReportRecord:
        """Persists the multi-dimensional quality scorecard and individual issue records."""
        dims = score_result.dimensions
        record = QualityReportRecord(
            version_id=version_id,
            overall_score=score_result.overall_score,
            grade=score_result.grade,
            grade_label=score_result.grade_label,
            completeness_score=dims["completeness"].score,
            validity_score=dims["validity"].score,
            uniqueness_score=dims["uniqueness"].score,
            consistency_score=dims["consistency"].score,
            is_trustworthy=score_result.is_trustworthy,
        )

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO quality_reports (id, version_id, overall_score, grade, grade_label,
                                             completeness_score, validity_score, uniqueness_score,
                                             consistency_score, is_trustworthy, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.version_id,
                    record.overall_score,
                    record.grade,
                    record.grade_label,
                    record.completeness_score,
                    record.validity_score,
                    record.uniqueness_score,
                    record.consistency_score,
                    1 if record.is_trustworthy else 0,
                    record.created_at,
                ),
            )

            # Persist individual detected issues if report provided
            if quality_report and quality_report.issues:
                issue_rows = [
                    (
                        generate_uuid(),
                        record.id,
                        issue.category.value,
                        issue.severity.value,
                        issue.column,
                        issue.description,
                        issue.affected_count,
                        issue.affected_percentage,
                        issue.suggested_action,
                        record.created_at,
                    )
                    for issue in quality_report.issues
                ]
                conn.executemany(
                    """
                    INSERT INTO quality_issues (id, report_id, category, severity, column_name,
                                                description, affected_count, affected_percentage,
                                                suggested_action, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    issue_rows,
                )

        return record

    def record_cleaning_job(
        self,
        source_version_id: str,
        target_version_id: str,
        cleaning_result: CleaningResult,
        quality_score_delta: float = 0.0,
    ) -> CleaningJobRecord:
        """Records an auditable cleaning job connecting two dataset versions."""
        job = CleaningJobRecord(
            source_version_id=source_version_id,
            target_version_id=target_version_id,
            total_operations=len(cleaning_result.steps),
            rows_modified=cleaning_result.delta.get("rows_removed", 0) + cleaning_result.delta.get("missing_cells_resolved", 0),
            quality_score_delta=quality_score_delta,
            execution_log_json=json.dumps([s.to_dict() for s in cleaning_result.steps]),
        )

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO cleaning_jobs (id, source_version_id, target_version_id, total_operations,
                                           rows_modified, quality_score_delta, execution_log_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.id,
                    job.source_version_id,
                    job.target_version_id,
                    job.total_operations,
                    job.rows_modified,
                    job.quality_score_delta,
                    job.execution_log_json,
                    job.created_at,
                ),
            )

        return job

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves dataset details by ID."""
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
            return dict(row) if row else None

    def get_dataset_versions(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Retrieves all versions of a dataset with their quality scores."""
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT v.*, q.overall_score, q.grade, q.completeness_score, q.validity_score,
                       q.uniqueness_score, q.consistency_score, q.is_trustworthy
                FROM dataset_versions v
                LEFT JOIN quality_reports q ON v.id = q.version_id
                WHERE v.dataset_id = ?
                ORDER BY v.version_number ASC
                """,
                (dataset_id,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def load_version_dataframe(self, version_id: str) -> pd.DataFrame:
        """Loads the DataFrame corresponding to a stored version from its Parquet file."""
        with self._connection() as conn:
            row = conn.execute("SELECT storage_path FROM dataset_versions WHERE id = ?", (version_id,)).fetchone()
            if not row:
                raise FileNotFoundError(f"Version ID '{version_id}' not found in database.")
            storage_path = Path(row["storage_path"])
            if not storage_path.exists():
                raise FileNotFoundError(f"Storage file '{storage_path}' missing from disk.")
            return pd.read_parquet(storage_path)
