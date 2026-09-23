"""Domain models for Dataset History and Quality Lineage.

Phase 6: V6.0 – V6.5
Defines structured entities for datasets, version lineage, quality reports,
issues, and cleaning jobs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


def current_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Dataset:
    """Logical dataset container."""

    name: str
    original_filename: str
    id: str = field(default_factory=generate_uuid)
    description: Optional[str] = None
    user_id: Optional[str] = None
    created_at: str = field(default_factory=current_utc_iso)
    updated_at: str = field(default_factory=current_utc_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DatasetVersion:
    """Immutable version snapshot pointing to an on-disk Parquet or CSV file."""

    dataset_id: str
    version_number: int
    storage_path: str
    row_count: int
    column_count: int
    file_size_bytes: int
    file_format: str = "parquet"
    parent_version_id: Optional[str] = None
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=current_utc_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityReportRecord:
    """Persisted quality evaluation metrics for a specific version."""

    version_id: str
    overall_score: float
    grade: str
    grade_label: str
    completeness_score: float
    validity_score: float
    uniqueness_score: float
    consistency_score: float
    is_trustworthy: bool
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=current_utc_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityIssueRecord:
    """Individual quality defect detected during quality evaluation."""

    report_id: str
    category: str
    severity: str
    description: str
    column_name: Optional[str] = None
    affected_count: int = 0
    affected_percentage: float = 0.0
    suggested_action: Optional[str] = None
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=current_utc_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CleaningJobRecord:
    """Records the execution of a transformation pipeline between two versions."""

    source_version_id: str
    target_version_id: str
    total_operations: int
    rows_modified: int
    quality_score_delta: float
    execution_log_json: str
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=current_utc_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
