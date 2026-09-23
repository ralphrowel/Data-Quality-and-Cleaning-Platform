"""Tests for DataQualityEngine (Phase 3)."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.quality import DataQualityEngine, IssueCategory, Severity


def test_missing_values_detection():
    """Verify missing values trigger appropriate severity and counts."""
    df = pd.DataFrame(
        {
            "col_complete": [1, 2, 3, 4, 5],
            "col_partial_missing": ["a", "b", "c", None, "e"],  # 20% missing -> Critical threshold
            "col_whitespace_missing": ["ok", "  ", "ok", "ok", "ok"],  # 20% missing
        }
    )

    engine = DataQualityEngine(critical_missing_threshold=20.0)
    report = engine.analyze(df)

    missing_issues = [i for i in report.issues if i.category == IssueCategory.MISSING]
    assert len(missing_issues) == 2

    partial_issue = next(i for i in missing_issues if i.column == "col_partial_missing")
    assert partial_issue.affected_count == 1
    assert partial_issue.severity == Severity.CRITICAL

    ws_issue = next(i for i in missing_issues if i.column == "col_whitespace_missing")
    assert ws_issue.affected_count == 1


def test_duplicate_rows_and_key_identifiers():
    """Verify detection of exact row duplicates and primary key collisions."""
    df = pd.DataFrame(
        {
            "user_id": ["u1", "u2", "u1", "u3"],
            "city": ["NY", "LA", "NY", "SF"],
        }
    )

    engine = DataQualityEngine()
    report = engine.analyze(df, id_columns=["user_id"])

    dup_issues = [i for i in report.issues if i.category == IssueCategory.DUPLICATE]
    assert len(dup_issues) == 2  # 1 for exact duplicate row, 1 for primary key collision

    exact_dup = next(i for i in dup_issues if i.column is None)
    assert exact_dup.affected_count == 1

    id_dup = next(i for i in dup_issues if i.column == "user_id")
    assert id_dup.affected_count == 2
    assert id_dup.severity == Severity.CRITICAL


def test_format_validation():
    """Verify email format rule validation."""
    df = pd.DataFrame(
        {
            "email": ["valid@example.com", "broken_email", "another@test.org", "bad@.com"],
        }
    )

    engine = DataQualityEngine()
    report = engine.analyze(df, format_rules={"email": "email"})

    format_issues = [i for i in report.issues if i.category == IssueCategory.INVALID_FORMAT]
    assert len(format_issues) == 1
    assert format_issues[0].affected_count == 2
    assert "broken_email" in format_issues[0].sample_values


def test_range_validation():
    """Verify bounds checking for numeric fields."""
    df = pd.DataFrame(
        {
            "age": [25, -5, 42, 135, 30],
        }
    )

    engine = DataQualityEngine()
    report = engine.analyze(df, range_rules={"age": {"min": 0, "max": 120}})

    range_issues = [i for i in report.issues if i.category == IssueCategory.INVALID_RANGE]
    assert len(range_issues) == 1
    assert range_issues[0].affected_count == 2
    assert -5 in range_issues[0].sample_values
    assert 135 in range_issues[0].sample_values


def test_casing_and_categorical_consistency():
    """Verify detection of casing discrepancies and unknown categories."""
    df = pd.DataFrame(
        {
            "gender": ["Male", "male", "Female", "MALE", "Female"],
            "plan": ["Basic", "Pro", "Enterprise", "Ultra_Invalid", "Basic"],
        }
    )

    engine = DataQualityEngine()
    report = engine.analyze(
        df,
        category_rules={"plan": ["Basic", "Pro", "Enterprise"]},
    )

    cat_issues = [i for i in report.issues if i.category == IssueCategory.INCONSISTENT_CATEGORY]
    # Expect 1 issue for casing in gender, 1 issue for unknown plan
    assert len(cat_issues) == 2

    gender_issue = next(i for i in cat_issues if i.column == "gender")
    assert gender_issue.affected_count == 3  # Male, male, MALE

    plan_issue = next(i for i in cat_issues if i.column == "plan")
    assert plan_issue.affected_count == 1
    assert "Ultra_Invalid" in plan_issue.sample_values


def test_outlier_detection_iqr():
    """Verify statistical outlier detection with IQR."""
    # Data with a clear outlier
    df = pd.DataFrame(
        {
            "val": [10, 11, 12, 10, 11, 12, 10, 11, 12, 10, 11, 12, 500],
        }
    )

    engine = DataQualityEngine(outlier_method="iqr")
    report = engine.analyze(df)

    outlier_issues = [i for i in report.issues if i.category == IssueCategory.OUTLIER]
    assert len(outlier_issues) == 1
    assert outlier_issues[0].affected_count == 1
    assert 500 in outlier_issues[0].sample_values


def test_quality_report_serialization():
    """Verify report serializes cleanly to JSON and dictionary."""
    df = pd.DataFrame({"col": [1, None, 3]})
    engine = DataQualityEngine()
    report = engine.analyze(df)

    data = report.to_dict()
    assert "total_issues_count" in data
    assert "issues_by_category" in data
    assert "issues_by_severity" in data

    json_str = report.to_json()
    parsed = json.loads(json_str)
    assert parsed["total_rows"] == 3


def test_netflix_dataset_quality_analysis():
    """Integration test: run quality checks on netflix_titles.csv."""
    netflix_path = Path("data/raw/netflix_titles.csv")
    if not netflix_path.exists():
        pytest.skip("netflix_titles.csv not found")

    df = pd.read_csv(netflix_path)
    engine = DataQualityEngine()

    report = engine.analyze(
        df,
        id_columns=["show_id"],
        range_rules={"release_year": {"min": 1900, "max": 2026}},
        category_rules={"type": ["Movie", "TV Show"]},
    )

    assert report.total_rows == 8807
    # Verify no primary key collisions
    pk_dups = [
        i
        for i in report.issues
        if i.category == IssueCategory.DUPLICATE and i.column == "show_id"
    ]
    assert len(pk_dups) == 0

    # Verify missing values were captured
    missing_issues = [i for i in report.issues if i.category == IssueCategory.MISSING]
    assert len(missing_issues) > 0
