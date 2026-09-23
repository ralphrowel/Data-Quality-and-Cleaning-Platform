"""Data Quality & Cleaning Platform — Data Quality Scoring Engine.

Phase 5: V5.0 – V5.3
Computes normalized multi-dimensional data quality scores:
- Completeness (missing data ratio)
- Validity (format & range compliance ratio)
- Uniqueness (duplicate records & key collisions)
- Consistency (categorical & casing standardizations)

Calculates weighted composite quality scores, assigns letter grades,
and measures before/after quality improvements.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.quality import DataQualityEngine, IssueCategory, QualityReport


@dataclass
class ScoreWeights:
    """Weight distribution for the 4 core data quality dimensions (must sum to 1.0)."""

    completeness: float = 0.30
    validity: float = 0.30
    uniqueness: float = 0.20
    consistency: float = 0.20

    def __post_init__(self):
        total = round(self.completeness + self.validity + self.uniqueness + self.consistency, 4)
        if total != 1.0:
            raise ValueError(f"Score weights must sum to 1.0 (got {total})")

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class DimensionScore:
    """Score and diagnostic metrics for an individual quality dimension."""

    name: str
    score: float  # 0.0 to 100.0
    weight: float
    weighted_score: float
    passed_items: int
    total_evaluated: int
    defects_count: int
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityScoreResult:
    """Composite quality score, dimensional breakdown, grade, and evaluation metadata."""

    overall_score: float  # 0.0 to 100.0
    grade: str  # A, B, C, D, F
    grade_label: str
    is_trustworthy: bool
    dimensions: Dict[str, DimensionScore]
    weights: ScoreWeights

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "grade": self.grade,
            "grade_label": self.grade_label,
            "is_trustworthy": self.is_trustworthy,
            "dimensions": {k: v.to_dict() for k, v in self.dimensions.items()},
            "weights": self.weights.to_dict(),
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


@dataclass
class ScoreComparison:
    """Quantifies before/after cleaning improvements in quality scores."""

    before: QualityScoreResult
    after: QualityScoreResult
    score_delta: float
    grade_improved: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "before_score": self.before.overall_score,
            "after_score": self.after.overall_score,
            "score_delta": self.score_delta,
            "before_grade": self.before.grade,
            "after_grade": self.after.grade,
            "grade_improved": self.grade_improved,
            "dimension_deltas": {
                dim: round(
                    self.after.dimensions[dim].score - self.before.dimensions[dim].score, 2
                )
                for dim in self.before.dimensions
            },
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class DataQualityScorer:
    """Calibrates and evaluates multi-dimensional data quality scores."""

    def __init__(self, weights: Optional[ScoreWeights] = None):
        self.weights = weights or ScoreWeights()
        self.quality_engine = DataQualityEngine()

    def score(
        self,
        df: pd.DataFrame,
        id_columns: Optional[List[str]] = None,
        range_rules: Optional[Dict[str, Dict[str, float]]] = None,
        format_rules: Optional[Dict[str, str]] = None,
        category_rules: Optional[Dict[str, List[str]]] = None,
        existing_report: Optional[QualityReport] = None,
    ) -> QualityScoreResult:
        """Evaluates a DataFrame and returns a comprehensive QualityScoreResult."""
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Expected a pandas DataFrame")

        total_rows = len(df)
        total_cells = df.size

        if total_rows == 0:
            return self._empty_score()

        report = existing_report or self.quality_engine.analyze(
            df,
            id_columns=id_columns,
            range_rules=range_rules,
            format_rules=format_rules,
            category_rules=category_rules,
        )

        # 1. Completeness Dimension (V5.0)
        missing_count = sum(
            issue.affected_count
            for issue in report.issues
            if issue.category == IssueCategory.MISSING
        )
        completeness_passed = max(0, total_cells - missing_count)
        completeness_score = round((completeness_passed / total_cells) * 100, 2)
        dim_completeness = DimensionScore(
            name="Completeness",
            score=completeness_score,
            weight=self.weights.completeness,
            weighted_score=round(completeness_score * self.weights.completeness, 2),
            passed_items=completeness_passed,
            total_evaluated=total_cells,
            defects_count=missing_count,
            details=f"{completeness_passed:,} of {total_cells:,} cells populated ({missing_count:,} missing).",
        )

        # 2. Validity Dimension (format, range, invalid values)
        validity_issues = [
            issue
            for issue in report.issues
            if issue.category in (IssueCategory.INVALID_FORMAT, IssueCategory.INVALID_RANGE, IssueCategory.INVALID_TYPE)
        ]
        validity_defects = sum(issue.affected_count for issue in validity_issues)
        # Total evaluated for validity is the sum of cells in tested columns
        validity_score = max(0.0, round((1.0 - (validity_defects / total_cells)) * 100, 2))
        dim_validity = DimensionScore(
            name="Validity",
            score=validity_score,
            weight=self.weights.validity,
            weighted_score=round(validity_score * self.weights.validity, 2),
            passed_items=total_cells - validity_defects,
            total_evaluated=total_cells,
            defects_count=validity_defects,
            details=f"{validity_defects:,} format or range violations detected across dataset cells.",
        )

        # 3. Uniqueness Dimension
        duplicate_issues = [
            issue for issue in report.issues if issue.category == IssueCategory.DUPLICATE
        ]
        duplicate_defects = sum(issue.affected_count for issue in duplicate_issues)
        uniqueness_score = max(0.0, round((1.0 - (duplicate_defects / total_rows)) * 100, 2))
        dim_uniqueness = DimensionScore(
            name="Uniqueness",
            score=uniqueness_score,
            weight=self.weights.uniqueness,
            weighted_score=round(uniqueness_score * self.weights.uniqueness, 2),
            passed_items=max(0, total_rows - duplicate_defects),
            total_evaluated=total_rows,
            defects_count=duplicate_defects,
            details=f"{duplicate_defects:,} duplicate rows or key collisions found in {total_rows:,} records.",
        )

        # 4. Consistency Dimension (casing variations, unknown categories)
        consistency_issues = [
            issue
            for issue in report.issues
            if issue.category == IssueCategory.INCONSISTENT_CATEGORY
        ]
        consistency_defects = sum(issue.affected_count for issue in consistency_issues)
        consistency_score = max(0.0, round((1.0 - (consistency_defects / total_cells)) * 100, 2))
        dim_consistency = DimensionScore(
            name="Consistency",
            score=consistency_score,
            weight=self.weights.consistency,
            weighted_score=round(consistency_score * self.weights.consistency, 2),
            passed_items=total_cells - consistency_defects,
            total_evaluated=total_cells,
            defects_count=consistency_defects,
            details=f"{consistency_defects:,} inconsistent categorical values or casing variants detected.",
        )

        # Composite score
        overall_score = round(
            dim_completeness.weighted_score
            + dim_validity.weighted_score
            + dim_uniqueness.weighted_score
            + dim_consistency.weighted_score,
            2,
        )
        overall_score = min(100.0, max(0.0, overall_score))

        grade, grade_label, is_trustworthy = self._assign_grade(overall_score)

        return QualityScoreResult(
            overall_score=overall_score,
            grade=grade,
            grade_label=grade_label,
            is_trustworthy=is_trustworthy,
            dimensions={
                "completeness": dim_completeness,
                "validity": dim_validity,
                "uniqueness": dim_uniqueness,
                "consistency": dim_consistency,
            },
            weights=self.weights,
        )

    def compare(
        self,
        before_df: pd.DataFrame,
        after_df: pd.DataFrame,
        id_columns: Optional[List[str]] = None,
        range_rules: Optional[Dict[str, Dict[str, float]]] = None,
        format_rules: Optional[Dict[str, str]] = None,
        category_rules: Optional[Dict[str, List[str]]] = None,
    ) -> ScoreComparison:
        """Calculates quality scores before and after cleaning to measure improvement."""
        score_before = self.score(
            before_df,
            id_columns=id_columns,
            range_rules=range_rules,
            format_rules=format_rules,
            category_rules=category_rules,
        )
        score_after = self.score(
            after_df,
            id_columns=id_columns,
            range_rules=range_rules,
            format_rules=format_rules,
            category_rules=category_rules,
        )

        delta = round(score_after.overall_score - score_before.overall_score, 2)
        grades_hierarchy = {"F": 0, "D": 1, "C": 2, "B": 3, "A": 4}
        improved = grades_hierarchy.get(score_after.grade, 0) > grades_hierarchy.get(score_before.grade, 0)

        return ScoreComparison(
            before=score_before,
            after=score_after,
            score_delta=delta,
            grade_improved=improved,
        )

    def _assign_grade(self, score: float) -> tuple[str, str, bool]:
        if score >= 90.0:
            return "A", "Excellent — Trustworthy for production analytics", True
        if score >= 80.0:
            return "B", "Good — Minor non-critical anomalies present", True
        if score >= 70.0:
            return "C", "Fair — Noticeable defects requiring analyst review", False
        if score >= 60.0:
            return "D", "Poor — High risk of biased or inaccurate analysis", False
        return "F", "Critical — Untrustworthy data; do not use for analysis", False

    def _empty_score(self) -> QualityScoreResult:
        empty_dim = lambda name, w: DimensionScore(
            name=name, score=0.0, weight=w, weighted_score=0.0, passed_items=0, total_evaluated=0, defects_count=0, details="Empty dataset."
        )
        return QualityScoreResult(
            overall_score=0.0,
            grade="F",
            grade_label="Empty dataset",
            is_trustworthy=False,
            dimensions={
                "completeness": empty_dim("Completeness", self.weights.completeness),
                "validity": empty_dim("Validity", self.weights.validity),
                "uniqueness": empty_dim("Uniqueness", self.weights.uniqueness),
                "consistency": empty_dim("Consistency", self.weights.consistency),
            },
            weights=self.weights,
        )
