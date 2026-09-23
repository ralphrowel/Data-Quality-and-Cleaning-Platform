"""Data Quality & Cleaning Platform — Data Quality Engine.

Phase 3: V3.0 – V3.7
Detects quality problems across key dimensions:
- MISSING (nulls, empty strings)
- DUPLICATE (exact rows, duplicate keys)
- INVALID_FORMAT (regex, email, phone, dates)
- INVALID_RANGE (bounds violation: min / max)
- INCONSISTENT_CATEGORY (casing discrepancies, unknown enum values)
- OUTLIER (statistical anomalies via IQR and Z-Score)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import re
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


class IssueCategory(str, Enum):
    MISSING = "MISSING"
    DUPLICATE = "DUPLICATE"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_RANGE = "INVALID_RANGE"
    INCONSISTENT_CATEGORY = "INCONSISTENT_CATEGORY"
    INVALID_TYPE = "INVALID_TYPE"
    OUTLIER = "OUTLIER"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


# Standard regex patterns
PATTERNS = {
    "email": re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
    "phone": re.compile(r"^\+?[0-9\s\-()]{7,20}$"),
    "iso_date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
}


@dataclass
class QualityIssue:
    """Represents a discrete data quality defect or anomaly."""

    category: IssueCategory
    severity: Severity
    column: Optional[str]
    description: str
    affected_count: int
    affected_percentage: float
    sample_values: List[Any] = field(default_factory=list)
    suggested_action: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        return data


@dataclass
class QualityReport:
    """Aggregated report of all data quality issues detected in a dataset."""

    total_rows: int
    total_columns: int
    total_issues_count: int
    issues_by_category: Dict[str, int]
    issues_by_severity: Dict[str, int]
    issues: List[QualityIssue]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "total_columns": self.total_columns,
            "total_issues_count": self.total_issues_count,
            "issues_by_category": self.issues_by_category,
            "issues_by_severity": self.issues_by_severity,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class DataQualityEngine:
    """Executes rule-based and statistical checks on pandas DataFrames."""

    def __init__(
        self,
        critical_missing_threshold: float = 20.0,
        outlier_method: str = "iqr",
        sample_limit: int = 5,
    ):
        self.critical_missing_threshold = critical_missing_threshold
        self.outlier_method = outlier_method
        self.sample_limit = sample_limit

    def analyze(
        self,
        df: pd.DataFrame,
        id_columns: Optional[List[str]] = None,
        range_rules: Optional[Dict[str, Dict[str, float]]] = None,
        format_rules: Optional[Dict[str, str]] = None,
        category_rules: Optional[Dict[str, List[str]]] = None,
    ) -> QualityReport:
        """Runs comprehensive quality checks and compiles a QualityReport."""
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Expected a pandas DataFrame")

        issues: List[QualityIssue] = []
        total_rows = len(df)
        total_columns = len(df.columns)

        if total_rows == 0:
            return QualityReport(
                total_rows=0,
                total_columns=total_columns,
                total_issues_count=0,
                issues_by_category={},
                issues_by_severity={},
                issues=[],
            )

        # 1. Missing values check (V3.1)
        issues.extend(self._check_missing_values(df, total_rows))

        # 2. Duplicate rows and keys check (V3.2)
        issues.extend(self._check_duplicates(df, total_rows, id_columns))

        # 3. Format validation (V3.3)
        if format_rules:
            issues.extend(self._check_formats(df, total_rows, format_rules))

        # 4. Range validation (V3.4)
        if range_rules:
            issues.extend(self._check_ranges(df, total_rows, range_rules))

        # 5. Categorical consistency checks (V3.5)
        issues.extend(self._check_categorical_consistency(df, total_rows, category_rules))

        # 6. Statistical outlier detection (V3.6)
        issues.extend(self._check_outliers(df, total_rows))

        # Summary statistics
        issues_by_category: Dict[str, int] = {}
        issues_by_severity: Dict[str, int] = {}

        for issue in issues:
            cat_name = issue.category.value
            sev_name = issue.severity.value
            issues_by_category[cat_name] = issues_by_category.get(cat_name, 0) + issue.affected_count
            issues_by_severity[sev_name] = issues_by_severity.get(sev_name, 0) + issue.affected_count

        return QualityReport(
            total_rows=total_rows,
            total_columns=total_columns,
            total_issues_count=sum(issues_by_category.values()),
            issues_by_category=issues_by_category,
            issues_by_severity=issues_by_severity,
            issues=issues,
        )

    def _check_missing_values(self, df: pd.DataFrame, total_rows: int) -> List[QualityIssue]:
        issues = []
        for col in df.columns:
            series = df[col]
            # Detect NaN or empty/whitespace-only strings
            if pd.api.types.is_string_dtype(series) or series.dtype == object:
                mask = series.isna() | (series.astype(str).str.strip() == "")
            else:
                mask = series.isna()

            null_count = int(mask.sum())
            if null_count > 0:
                null_pct = round((null_count / total_rows) * 100, 2)
                severity = (
                    Severity.CRITICAL
                    if null_pct >= self.critical_missing_threshold
                    else Severity.WARNING
                )
                issues.append(
                    QualityIssue(
                        category=IssueCategory.MISSING,
                        severity=severity,
                        column=col,
                        description=f"Column '{col}' has {null_count:,} missing values ({null_pct}%).",
                        affected_count=null_count,
                        affected_percentage=null_pct,
                        suggested_action="Impute with default/mode/median or drop if non-critical.",
                    )
                )
        return issues

    def _check_duplicates(
        self, df: pd.DataFrame, total_rows: int, id_columns: Optional[List[str]]
    ) -> List[QualityIssue]:
        issues = []

        # Exact duplicate rows
        dup_mask = df.duplicated()
        dup_count = int(dup_mask.sum())
        if dup_count > 0:
            dup_pct = round((dup_count / total_rows) * 100, 2)
            issues.append(
                QualityIssue(
                    category=IssueCategory.DUPLICATE,
                    severity=Severity.WARNING,
                    column=None,
                    description=f"Found {dup_count:,} exact duplicate rows ({dup_pct}%).",
                    affected_count=dup_count,
                    affected_percentage=dup_pct,
                    suggested_action="Deduplicate rows preserving first or last occurrence.",
                )
            )

        # Primary key identifier duplicates
        if id_columns:
            for key_col in id_columns:
                if key_col in df.columns:
                    key_dup_mask = df.duplicated(subset=[key_col], keep=False)
                    key_dup_count = int(key_dup_mask.sum())
                    if key_dup_count > 0:
                        key_dup_pct = round((key_dup_count / total_rows) * 100, 2)
                        samples = df.loc[key_dup_mask, key_col].head(self.sample_limit).tolist()
                        issues.append(
                            QualityIssue(
                                category=IssueCategory.DUPLICATE,
                                severity=Severity.CRITICAL,
                                column=key_col,
                                description=f"Primary key identifier '{key_col}' has {key_dup_count:,} duplicate occurrences.",
                                affected_count=key_dup_count,
                                affected_percentage=key_dup_pct,
                                sample_values=samples,
                                suggested_action="Verify identifier generation or deduplicate on primary key.",
                            )
                        )
        return issues

    def _check_formats(
        self, df: pd.DataFrame, total_rows: int, format_rules: Dict[str, str]
    ) -> List[QualityIssue]:
        issues = []
        for col, format_name in format_rules.items():
            if col not in df.columns:
                continue

            series = df[col].dropna().astype(str).str.strip()
            if len(series) == 0:
                continue

            regex = PATTERNS.get(format_name.lower())
            if regex is None:
                # Treat as custom regex pattern
                try:
                    regex = re.compile(format_name)
                except re.error:
                    continue

            invalid_mask = ~series.str.match(regex)
            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                invalid_pct = round((invalid_count / total_rows) * 100, 2)
                sample_invalids = series[invalid_mask].head(self.sample_limit).tolist()
                issues.append(
                    QualityIssue(
                        category=IssueCategory.INVALID_FORMAT,
                        severity=Severity.WARNING,
                        column=col,
                        description=f"Column '{col}' has {invalid_count:,} values failing format rule '{format_name}'.",
                        affected_count=invalid_count,
                        affected_percentage=invalid_pct,
                        sample_values=sample_invalids,
                        suggested_action=f"Normalize or correct values to conform with '{format_name}'.",
                    )
                )
        return issues

    def _check_ranges(
        self, df: pd.DataFrame, total_rows: int, range_rules: Dict[str, Dict[str, float]]
    ) -> List[QualityIssue]:
        issues = []
        for col, bounds in range_rules.items():
            if col not in df.columns or not pd.api.types.is_numeric_dtype(df[col]):
                continue

            series = df[col].dropna()
            min_val = bounds.get("min")
            max_val = bounds.get("max")

            invalid_mask = pd.Series(False, index=series.index)
            desc_parts = []
            if min_val is not None:
                invalid_mask |= series < min_val
                desc_parts.append(f"< {min_val}")
            if max_val is not None:
                invalid_mask |= series > max_val
                desc_parts.append(f"> {max_val}")

            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                invalid_pct = round((invalid_count / total_rows) * 100, 2)
                samples = series[invalid_mask].head(self.sample_limit).tolist()
                issues.append(
                    QualityIssue(
                        category=IssueCategory.INVALID_RANGE,
                        severity=Severity.WARNING,
                        column=col,
                        description=f"Column '{col}' has {invalid_count:,} values out of range ({' or '.join(desc_parts)}).",
                        affected_count=invalid_count,
                        affected_percentage=invalid_pct,
                        sample_values=samples,
                        suggested_action="Cap/clamp values within allowed boundaries or nullify invalid entries.",
                    )
                )
        return issues

    def _check_categorical_consistency(
        self,
        df: pd.DataFrame,
        total_rows: int,
        category_rules: Optional[Dict[str, List[str]]],
    ) -> List[QualityIssue]:
        issues = []
        text_cols = df.select_dtypes(include=["object", "str"]).columns

        for col in text_cols:
            series = df[col].dropna().astype(str).str.strip()
            if len(series) == 0:
                continue

            # 1. Check casing inconsistency (e.g. 'Male', 'male', 'MALE')
            raw_unique = series.unique()
            lower_map: Dict[str, List[str]] = {}
            for val in raw_unique:
                key = val.lower()
                lower_map.setdefault(key, []).append(val)

            inconsistent_groups = [vals for vals in lower_map.values() if len(vals) > 1]
            if inconsistent_groups:
                inconsistent_variants = [v for group in inconsistent_groups for v in group]
                affected_count = int(series.isin(inconsistent_variants).sum())
                affected_pct = round((affected_count / total_rows) * 100, 2)
                sample_display = [f"{{{', '.join(group)}}}" for group in inconsistent_groups[:self.sample_limit]]

                issues.append(
                    QualityIssue(
                        category=IssueCategory.INCONSISTENT_CATEGORY,
                        severity=Severity.INFO,
                        column=col,
                        description=f"Column '{col}' contains case inconsistencies: {'; '.join(sample_display)}.",
                        affected_count=affected_count,
                        affected_percentage=affected_pct,
                        sample_values=sample_display,
                        suggested_action="Standardize casing using uppercase, lowercase, or titlecase mapping.",
                    )
                )

            # 2. Check predefined allowed categories
            if category_rules and col in category_rules:
                allowed = set(category_rules[col])
                unknown_mask = ~series.isin(allowed)
                unknown_count = int(unknown_mask.sum())
                if unknown_count > 0:
                    unknown_pct = round((unknown_count / total_rows) * 100, 2)
                    sample_unknowns = series[unknown_mask].head(self.sample_limit).tolist()
                    issues.append(
                        QualityIssue(
                            category=IssueCategory.INCONSISTENT_CATEGORY,
                            severity=Severity.WARNING,
                            column=col,
                            description=f"Column '{col}' has {unknown_count:,} values not in configured categories.",
                            affected_count=unknown_count,
                            affected_percentage=unknown_pct,
                            sample_values=sample_unknowns,
                            suggested_action="Map unknown categories to defined terms or label as 'Other'.",
                        )
                    )
        return issues

    def _check_outliers(self, df: pd.DataFrame, total_rows: int) -> List[QualityIssue]:
        issues = []
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 10:
                continue

            if self.outlier_method == "iqr":
                q25 = float(series.quantile(0.25))
                q75 = float(series.quantile(0.75))
                iqr = q75 - q25
                if iqr <= 0:
                    continue
                lower_bound = q25 - 1.5 * iqr
                upper_bound = q75 + 1.5 * iqr
                outlier_mask = (series < lower_bound) | (series > upper_bound)
            else:  # z-score
                mean = series.mean()
                std = series.std(ddof=1)
                if std == 0:
                    continue
                z_scores = np.abs((series - mean) / std)
                outlier_mask = z_scores > 3.0

            outlier_count = int(outlier_mask.sum())
            if outlier_count > 0:
                outlier_pct = round((outlier_count / total_rows) * 100, 2)
                sample_outliers = series[outlier_mask].head(self.sample_limit).tolist()
                issues.append(
                    QualityIssue(
                        category=IssueCategory.OUTLIER,
                        severity=Severity.INFO,
                        column=col,
                        description=f"Column '{col}' has {outlier_count:,} statistical outliers ({self.outlier_method.upper()} method).",
                        affected_count=outlier_count,
                        affected_percentage=outlier_pct,
                        sample_values=sample_outliers,
                        suggested_action="Inspect domain context; consider winsorizing or capping if erroneous.",
                    )
                )
        return issues
