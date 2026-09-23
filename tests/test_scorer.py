"""Tests for DataQualityScorer (Phase 5)."""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from src.cleaner import DataCleaningEngine
from src.scorer import DataQualityScorer, ScoreWeights


def test_score_weights_validation():
    """Verify weights validation ensures sum equals 1.0."""
    valid_weights = ScoreWeights(completeness=0.4, validity=0.3, uniqueness=0.2, consistency=0.1)
    assert valid_weights.completeness == 0.4

    with pytest.raises(ValueError, match="must sum to 1.0"):
        ScoreWeights(completeness=0.5, validity=0.5, uniqueness=0.5, consistency=0.5)


def test_perfect_dataset_score():
    """A pristine dataset should receive a near 100% Grade A score."""
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "name": ["Alice", "Bob", "Charlie", "David"],
            "score": [95.0, 88.0, 92.0, 100.0],
        }
    )

    scorer = DataQualityScorer()
    result = scorer.score(df, id_columns=["id"], range_rules={"score": {"min": 0, "max": 100}})

    assert result.overall_score == 100.0
    assert result.grade == "A"
    assert result.is_trustworthy is True
    assert result.dimensions["completeness"].score == 100.0
    assert result.dimensions["uniqueness"].score == 100.0


def test_dirty_dataset_score():
    """A dataset with missing values, duplicate IDs, and range violations should get penalized."""
    df = pd.DataFrame(
        {
            "id": [1, 1, 2, 3],  # duplicate ID
            "age": [25, -10, None, 40],  # out of range (-10) + missing
            "status": ["Active", "active", "ACTIVE", "Pending"],  # casing inconsistency
        }
    )

    scorer = DataQualityScorer()
    result = scorer.score(df, id_columns=["id"], range_rules={"age": {"min": 0, "max": 120}})

    assert result.overall_score < 100.0
    assert result.dimensions["completeness"].score < 100.0
    assert result.dimensions["validity"].score < 100.0
    assert result.dimensions["uniqueness"].score < 100.0
    assert result.dimensions["consistency"].score < 100.0


def test_score_serialization():
    """Verify result serializes cleanly to JSON and dictionary."""
    df = pd.DataFrame({"col": [1, 2, 3]})
    scorer = DataQualityScorer()
    result = scorer.score(df)

    data = result.to_dict()
    assert "overall_score" in data
    assert "grade" in data
    assert "dimensions" in data

    json_str = result.to_json()
    parsed = json.loads(json_str)
    assert parsed["overall_score"] == 100.0


def test_score_comparison_before_after():
    """Verify before/after comparison shows positive score delta after cleaning."""
    raw_df = pd.DataFrame(
        {
            "id": [1, 2, 2, 3],  # exact duplicate row at index 1 and 2
            "city": ["NY", "LA", "LA", "SF"],
            "val": [10.0, 20.0, 20.0, None],  # missing value at index 3
        }
    )

    cleaner = DataCleaningEngine()
    clean_result = cleaner.clean(
        raw_df,
        drop_duplicates_subset=True,
        missing_strategies={"val": {"strategy": "mean"}},
    )

    scorer = DataQualityScorer()
    comparison = scorer.compare(raw_df, clean_result.cleaned_df)

    assert comparison.score_delta > 0
    assert comparison.after.overall_score > comparison.before.overall_score
    assert comparison.after.dimensions["completeness"].score == 100.0
    assert comparison.after.dimensions["uniqueness"].score == 100.0


def test_netflix_scoring_improvement():
    """Integration test: verify quality scoring on netflix_titles.csv."""
    netflix_path = Path("data/raw/netflix_titles.csv")
    if not netflix_path.exists():
        pytest.skip("netflix_titles.csv not found")

    raw_df = pd.read_csv(netflix_path)

    cleaner = DataCleaningEngine()
    clean_result = cleaner.clean(
        raw_df,
        strip_whitespace=True,
        missing_strategies={
            "director": {"strategy": "constant", "value": "Unknown Director"},
            "country": {"strategy": "constant", "value": "Unknown Country"},
            "cast": {"strategy": "constant", "value": "Unknown Cast"},
            "rating": {"strategy": "mode"},
        },
    )

    scorer = DataQualityScorer()
    comparison = scorer.compare(raw_df, clean_result.cleaned_df)

    # Completeness should improve significantly after imputing directors, countries, and casts
    assert (
        comparison.after.dimensions["completeness"].score
        > comparison.before.dimensions["completeness"].score
    )
    assert comparison.score_delta > 0
