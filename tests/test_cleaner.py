"""Tests for DataCleaningEngine (Phase 4)."""

from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.cleaner import DataCleaningEngine


def test_whitespace_and_column_normalization():
    """Verify column header and string whitespace stripping."""
    df = pd.DataFrame(
        {
            " name ": ["  Alice ", "Bob  ", " Charlie"],
            "city": [" New York", "Los Angeles ", "Chicago "],
        }
    )

    cleaner = DataCleaningEngine()
    result = cleaner.clean(df, strip_whitespace=True, normalize_column_names=True)

    assert "name" in result.cleaned_df.columns
    assert " name " not in result.cleaned_df.columns
    assert result.cleaned_df["name"].tolist() == ["Alice", "Bob", "Charlie"]
    assert result.cleaned_df["city"].tolist() == ["New York", "Los Angeles", "Chicago"]
    assert len(result.steps) >= 2


def test_casing_and_categorical_mapping():
    """Verify categorical value mapping and casing standardization."""
    df = pd.DataFrame(
        {
            "gender": ["m", "M", "female", "F"],
            "status": ["active", "PENDING", "Inactive", "active"],
        }
    )

    cleaner = DataCleaningEngine()
    result = cleaner.clean(
        df,
        categorical_mappings={"gender": {"m": "Male", "M": "Male", "female": "Female", "F": "Female"}},
        casing_rules={"status": "title"},
    )

    assert result.cleaned_df["gender"].tolist() == ["Male", "Male", "Female", "Female"]
    assert result.cleaned_df["status"].tolist() == ["Active", "Pending", "Inactive", "Active"]


def test_date_normalization():
    """Verify mixed date strings are normalized to ISO YYYY-MM-DD."""
    df = pd.DataFrame(
        {
            "date": ["09/25/2021", "2020-01-15", "December 1, 2019", None],
        }
    )

    cleaner = DataCleaningEngine()
    result = cleaner.clean(df, date_columns=["date"])

    expected = ["2021-09-25", "2020-01-15", "2019-12-01", np.nan]
    actual = result.cleaned_df["date"].tolist()
    assert actual[:3] == expected[:3]
    assert pd.isna(actual[3])


def test_range_enforcement_clamp_and_nullify():
    """Verify numerical values outside range are clamped or nullified."""
    df = pd.DataFrame(
        {
            "age": [25, -5, 150, 40],
            "score": [90, 110, -10, 85],
        }
    )

    cleaner = DataCleaningEngine()
    result = cleaner.clean(
        df,
        range_rules={
            "age": {"min": 0, "max": 120, "action": "clamp"},
            "score": {"min": 0, "max": 100, "action": "nullify"},
        },
    )

    assert result.cleaned_df["age"].tolist() == [25, 0, 120, 40]
    assert result.cleaned_df["score"].iloc[0] == 90
    assert pd.isna(result.cleaned_df["score"].iloc[1])  # 110 -> null
    assert pd.isna(result.cleaned_df["score"].iloc[2])  # -10 -> null


def test_missing_value_imputation():
    """Verify imputation strategies: mean, median, mode, constant, drop."""
    df = pd.DataFrame(
        {
            "num_mean": [10.0, 20.0, 30.0, None],  # mean of 10,20,30 = 20.0
            "num_median": [10.0, 20.0, 100.0, None],  # median = 20.0
            "cat_mode": ["A", "A", "B", None],  # mode = 'A'
            "cat_const": ["X", None, "Z", "W"],
        }
    )

    cleaner = DataCleaningEngine()
    result = cleaner.clean(
        df,
        missing_strategies={
            "num_mean": {"strategy": "mean"},
            "num_median": {"strategy": "median"},
            "cat_mode": {"strategy": "mode"},
            "cat_const": {"strategy": "constant", "value": "Unknown"},
        },
    )

    assert result.cleaned_df["num_mean"].tolist() == [10.0, 20.0, 30.0, 20.0]
    assert result.cleaned_df["num_median"].tolist() == [10.0, 20.0, 100.0, 20.0]
    assert result.cleaned_df["cat_mode"].tolist() == ["A", "A", "B", "A"]
    assert result.cleaned_df["cat_const"].tolist() == ["X", "Unknown", "Z", "W"]
    assert result.after_stats["missing_cells"] == 0


def test_duplicate_removal():
    """Verify duplicate row dropping."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 2, 3],
            "val": ["a", "b", "b", "c"],
        }
    )

    cleaner = DataCleaningEngine()
    result = cleaner.clean(df, drop_duplicates_subset=True)

    assert len(result.cleaned_df) == 3
    assert result.delta["duplicates_removed"] == 1


def test_safe_csv_export_formula_injection_defense():
    """Verify cells starting with =, +, -, @ are sanitized on CSV export."""
    df = pd.DataFrame(
        {
            "payload": ["=cmd|' /C calc'!A0", "+SUM(A1:A10)", "-2+3", "@alert(1)", "normal_text"],
        }
    )

    cleaner = DataCleaningEngine()
    result = cleaner.clean(df)

    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_path = Path(tmp_dir) / "export_safe.csv"
        result.export_safe_csv(csv_path)

        content = csv_path.read_text(encoding="utf-8")
        assert "'=cmd|" in content
        assert "'+SUM" in content
        assert "'-2+3" in content
        assert "'@alert" in content
        assert "normal_text" in content


def test_parquet_export_and_type_preservation():
    """Verify Parquet export preserves nullable types."""
    df = pd.DataFrame(
        {
            "id": pd.Series([1, 2, None], dtype="Int64"),
            "val": ["x", "y", "z"],
        }
    )

    cleaner = DataCleaningEngine()
    result = cleaner.clean(df)

    with tempfile.TemporaryDirectory() as tmp_dir:
        pq_path = Path(tmp_dir) / "test.parquet"
        result.export_parquet(pq_path)
        assert pq_path.exists()

        reloaded = pd.read_parquet(pq_path)
        assert len(reloaded) == 3
        assert reloaded["id"].isna().sum() == 1


def test_netflix_cleaning_pipeline():
    """Integration test: clean netflix_titles.csv."""
    netflix_path = Path("data/raw/netflix_titles.csv")
    if not netflix_path.exists():
        pytest.skip("netflix_titles.csv not found")

    df = pd.read_csv(netflix_path)
    cleaner = DataCleaningEngine()

    result = cleaner.clean(
        df,
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

    assert result.cleaned_df["director"].isna().sum() == 0
    assert result.cleaned_df["country"].isna().sum() == 0
    assert result.cleaned_df["cast"].isna().sum() == 0
    assert result.cleaned_df["rating"].isna().sum() == 0
    assert result.delta["missing_cells_resolved"] > 4000
    assert len(result.steps) >= 5
