"""Edge Case & Boundary Tests (Phase 10 — V10.1).

Covers critical boundary cases specified in Section 14 of the project planner:
- Empty datasets (0 rows)
- Single row / single column datasets
- Pristine datasets (0 missing, 0 duplicates)
- 100% missing values in a column
- 100% duplicate records
- Malformed and impossible dates
- Mixed types in single column
- Extreme numerical values (np.inf, -np.inf, 1e18)
- Unusual column headers (whitespace, unicode, emojis, symbols)
"""

import numpy as np
import pandas as pd
import pytest

from src.cleaner import DataCleaningEngine
from src.profiler import DataProfiler
from src.quality import DataQualityEngine, IssueCategory, Severity
from src.scorer import DataQualityScorer


def test_empty_dataframe_profiling():
    """Verify DataProfiler safely handles empty DataFrames (0 rows) without ZeroDivisionError."""
    df_empty = pd.DataFrame(columns=["id", "name", "val"])
    profiler = DataProfiler()
    result = profiler.profile(df_empty)

    assert result.summary.total_rows == 0
    assert result.summary.total_columns == 3
    assert result.summary.total_cells == 0
    assert result.summary.missing_percentage == 0.0
    assert result.summary.duplicate_rows == 0
    assert result.summary.duplicate_percentage == 0.0
    assert len(result.columns) == 3


def test_empty_dataframe_quality_and_scoring():
    """Verify QualityEngine and Scorer handle empty DataFrames gracefully."""
    df_empty = pd.DataFrame(columns=["id", "score"])
    engine = DataQualityEngine()
    report = engine.analyze(df_empty)
    assert report.total_rows == 0
    assert len(report.issues) == 0

    scorer = DataQualityScorer()
    score_res = scorer.score(df_empty)
    # Empty dataset receives base 100.0 or 0.0 depending on zero handling, without crashing
    assert isinstance(score_res.overall_score, float)
    assert score_res.grade in ["A", "B", "C", "D", "F"]


def test_single_cell_dataset():
    """Verify 1 row x 1 column dataset operates cleanly across profiler, quality, scorer, cleaner."""
    df = pd.DataFrame({"single_col": ["alpha"]})

    profiler = DataProfiler()
    prof = profiler.profile(df)
    assert prof.summary.total_rows == 1
    assert prof.summary.total_columns == 1

    cleaner = DataCleaningEngine()
    clean_res = cleaner.clean(df, casing_rules={"single_col": "upper"})
    assert clean_res.cleaned_df["single_col"].iloc[0] == "ALPHA"


def test_100_percent_missing_column():
    """Verify handling when an entire column is NaN / None."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "completely_null": [None, np.nan, None, float("nan")],
            "partially_null": [10.0, None, 30.0, None],
        }
    )

    # Profiling
    profiler = DataProfiler()
    prof = profiler.profile(df)
    assert prof.columns["completely_null"].null_count == 4
    assert prof.columns["completely_null"].null_percentage == 100.0

    # Quality check
    engine = DataQualityEngine()
    report = engine.analyze(df)
    col_null_issues = [
        i for i in report.issues
        if i.column == "completely_null" and i.category == IssueCategory.MISSING
    ]
    assert len(col_null_issues) == 1
    assert col_null_issues[0].affected_percentage == 100.0

    # Cleaning: mean/median on all-NaN shouldn't crash
    cleaner = DataCleaningEngine()
    clean_res = cleaner.clean(
        df,
        missing_strategies={
            "completely_null": {"strategy": "constant", "value": "N/A"},
            "partially_null": {"strategy": "mean"},
        },
    )
    assert clean_res.cleaned_df["completely_null"].tolist() == ["N/A", "N/A", "N/A", "N/A"]
    assert clean_res.cleaned_df["partially_null"].isna().sum() == 0


def test_pristine_dataset_no_missing_no_duplicates():
    """Verify a pristine dataset produces zero issues and a 100% Grade A score."""
    df = pd.DataFrame(
        {
            "user_id": [101, 102, 103, 104, 105],
            "email": ["u1@ex.com", "u2@ex.com", "u3@ex.com", "u4@ex.com", "u5@ex.com"],
            "age": [20, 25, 30, 35, 40],
        }
    )

    engine = DataQualityEngine()
    report = engine.analyze(
        df,
        id_columns=["user_id"],
        format_rules={"email": "email"},
        range_rules={"age": {"min": 18, "max": 65}},
    )
    assert len(report.issues) == 0

    scorer = DataQualityScorer()
    score_res = scorer.score(
        df,
        id_columns=["user_id"],
        format_rules={"email": "email"},
        range_rules={"age": {"min": 18, "max": 65}},
    )
    assert score_res.overall_score == 100.0
    assert score_res.grade == "A"
    assert score_res.is_trustworthy is True


def test_100_percent_duplicate_rows():
    """Verify datasets where every row is an exact duplicate."""
    df = pd.DataFrame(
        {
            "id": [1, 1, 1, 1, 1],
            "item": ["apple", "apple", "apple", "apple", "apple"],
        }
    )

    profiler = DataProfiler()
    prof = profiler.profile(df)
    assert prof.summary.duplicate_rows == 4
    assert prof.summary.duplicate_percentage == 80.0

    cleaner = DataCleaningEngine()
    clean_res = cleaner.clean(df, drop_duplicates_subset=True)
    assert len(clean_res.cleaned_df) == 1
    assert clean_res.delta.get("rows_removed", 0) == 4


def test_malformed_and_impossible_dates():
    """Verify mixed, corrupted, and unparseable date strings."""
    df = pd.DataFrame(
        {
            "event_date": [
                "2023-01-15",
                "15/01/2023",
                "not_a_date",
                "9999-99-99",
                "2023-02-29",  # non-leap year invalid date
                None,
            ]
        }
    )

    cleaner = DataCleaningEngine()
    clean_res = cleaner.clean(df, date_columns=["event_date"])
    # Valid date parsed to ISO YYYY-MM-DD, invalid dates safely coerced to NaT/None
    assert clean_res.cleaned_df["event_date"].iloc[0] == "2023-01-15"
    assert clean_res.cleaned_df["event_date"].iloc[1] == "2023-01-15"
    assert clean_res.cleaned_df["event_date"].iloc[2] is None or pd.isna(clean_res.cleaned_df["event_date"].iloc[2])


def test_mixed_types_in_single_column():
    """Verify column containing mixed datatypes (ints, floats, strings, bools)."""
    df = pd.DataFrame({"mixed_data": [100, "200", 300.5, True, "invalid", None]})

    profiler = DataProfiler()
    prof = profiler.profile(df)
    assert prof.columns["mixed_data"].null_count == 1
    assert prof.columns["mixed_data"].semantic_type in ["text", "numeric"]

    cleaner = DataCleaningEngine()
    clean_res = cleaner.clean(
        df,
        type_conversions={"mixed_data": "float"},
        missing_strategies={"mixed_data": {"strategy": "constant", "value": 0.0}},
    )
    # The column is now strongly typed as float64
    assert pd.api.types.is_float_dtype(clean_res.cleaned_df["mixed_data"])
    assert clean_res.cleaned_df["mixed_data"].iloc[0] == 100.0
    assert clean_res.cleaned_df["mixed_data"].iloc[1] == 200.0
    assert clean_res.cleaned_df["mixed_data"].iloc[2] == 300.5
    assert clean_res.cleaned_df["mixed_data"].iloc[3] == 1.0
    # 'invalid' was safely coerced to NaN without unhandled error
    assert pd.isna(clean_res.cleaned_df["mixed_data"].iloc[4])
    # Initial None was filled by missing_strategies constant 0.0
    assert clean_res.cleaned_df["mixed_data"].iloc[5] == 0.0



def test_extreme_numerical_values():
    """Verify handling of inf, -inf, and massive numbers without crash."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "val": [10.0, float("inf"), float("-inf"), 1e18, -1e18],
        }
    )

    profiler = DataProfiler()
    prof = profiler.profile(df)
    assert prof.summary.total_rows == 5

    # Outlier detection should run safely
    engine = DataQualityEngine()
    report = engine.analyze(df)
    assert report is not None


def test_unusual_column_headers():
    """Verify column headers with whitespace, punctuation, and emojis."""
    df = pd.DataFrame(
        {
            " First Name ": ["John"],
            "User-Email@Address#": ["john@test.com"],
            "Score ($)": [95],
            "🚀 Status": ["active"],
        }
    )

    cleaner = DataCleaningEngine()
    clean_res = cleaner.clean(df, normalize_column_names=True)
    cols = clean_res.cleaned_df.columns.tolist()

    assert "First Name" in cols
    assert " First Name " not in cols
    assert cols[0] == "First Name"

