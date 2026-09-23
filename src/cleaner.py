"""Data Quality & Cleaning Platform — Deterministic Data Cleaning Engine.

Phase 4: V4.0 – V4.7
Executes an ordered, deterministic transformation pipeline:
1. Structural Normalization (column names, empty rows/columns)
2. Whitespace & Text Trimming
3. Categorical & Casing Standardization
4. Date Normalization (ISO-8601 YYYY-MM-DD)
5. Out-of-Range & Invalid Format Coercion (convert to NaN/Null)
6. Duplicate Removal (exact rows or primary key subset)
7. Missing-Value Imputation (drop, mean, median, mode, constant, ffill, bfill)
8. Strict Type Casting (nullable types)
9. Formula-Injection Sanitization (on export)
10. Before / After Comparison & Auditable Cleaning Log
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


@dataclass
class CleaningStep:
    """Record of a single atomic cleaning transformation."""

    step_number: int
    operation: str
    target_column: Optional[str]
    parameters: Dict[str, Any]
    rows_affected: int
    details: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CleaningResult:
    """Encapsulates the cleaned DataFrame, audit log, and before/after metrics."""

    cleaned_df: pd.DataFrame
    steps: List[CleaningStep]
    before_stats: Dict[str, Any]
    after_stats: Dict[str, Any]
    delta: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "before_stats": self.before_stats,
            "after_stats": self.after_stats,
            "delta": self.delta,
            "steps": [step.to_dict() for step in self.steps],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def export_parquet(self, filepath: str | Path) -> None:
        """Saves cleaned DataFrame to Apache Parquet format preserving exact types."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.cleaned_df.to_parquet(path, index=False, engine="pyarrow")

    def export_safe_csv(self, filepath: str | Path) -> None:
        """Saves cleaned DataFrame to CSV with formula injection sanitization.

        Prepends a single quote to cells beginning with '=', '+', '-', '@', '\\t', '\\r'
        to protect against formula injection when opened in Excel/Calc.
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        export_df = self.cleaned_df.copy()
        formula_triggers = re.compile(r"^[\=\+\-\@\t\r]")

        str_cols = export_df.select_dtypes(include=["object", "str"]).columns
        for col in str_cols:
            export_df[col] = export_df[col].apply(
                lambda val: f"'{val}" if isinstance(val, str) and formula_triggers.match(val) else val
            )

        export_df.to_csv(path, index=False, encoding="utf-8")


class DataCleaningEngine:
    """Executes deterministic cleaning transformations and tracks lineage."""

    def __init__(self):
        self.steps: List[CleaningStep] = []

    def clean(
        self,
        df: pd.DataFrame,
        strip_whitespace: bool = True,
        normalize_column_names: bool = True,
        categorical_mappings: Optional[Dict[str, Dict[str, str]]] = None,
        casing_rules: Optional[Dict[str, str]] = None,  # col -> 'lower', 'upper', 'title'
        date_columns: Optional[List[str]] = None,
        range_rules: Optional[Dict[str, Dict[str, float]]] = None,  # col -> {'min': x, 'max': y, 'action': 'clamp'|'nullify'}
        drop_duplicates_subset: Optional[List[str] | bool] = None,  # True for all cols or list of cols
        missing_strategies: Optional[Dict[str, Dict[str, Any]]] = None,
        # e.g.: {'col': {'strategy': 'mean'|'median'|'mode'|'constant'|'drop', 'value': '...'}}
        type_conversions: Optional[Dict[str, str]] = None,  # col -> 'int', 'float', 'str', 'datetime'
    ) -> CleaningResult:
        """Executes the deterministic 13-step transformation pipeline."""
        if not isinstance(df, pd.DataFrame):
            raise TypeError("Expected a pandas DataFrame")

        self.steps = []
        working_df = df.copy()

        # Capture before statistics
        before_stats = self._calc_stats(working_df)

        # Step 1: Normalize column names (strip whitespace)
        if normalize_column_names:
            old_cols = list(working_df.columns)
            new_cols = [str(c).strip() for c in old_cols]
            renamed_count = sum(1 for o, n in zip(old_cols, new_cols) if o != n)
            if renamed_count > 0:
                working_df.columns = new_cols
                self._record_step(
                    operation="normalize_column_names",
                    target_column=None,
                    parameters={},
                    rows_affected=renamed_count,
                    details=f"Stripped whitespace from {renamed_count} column headers.",
                )

        # Step 2: Whitespace trimming across string columns
        if strip_whitespace:
            str_cols = working_df.select_dtypes(include=["object", "str"]).columns
            total_stripped = 0
            for col in str_cols:
                original = working_df[col].dropna().astype(str)
                stripped = original.str.strip()
                diff = (original != stripped).sum()
                if diff > 0:
                    working_df[col] = working_df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
                    total_stripped += int(diff)
            if total_stripped > 0:
                self._record_step(
                    operation="strip_whitespace",
                    target_column=None,
                    parameters={},
                    rows_affected=total_stripped,
                    details=f"Trimmed leading/trailing whitespaces in {total_stripped:,} cells.",
                )

        # Step 3: Categorical & Casing standardization
        if casing_rules:
            for col, case_type in casing_rules.items():
                if col in working_df.columns and (pd.api.types.is_string_dtype(working_df[col]) or working_df[col].dtype == object):
                    non_nulls = working_df[col].dropna()
                    if case_type == "lower":
                        transformed = non_nulls.str.lower()
                    elif case_type == "upper":
                        transformed = non_nulls.str.upper()
                    elif case_type == "title":
                        transformed = non_nulls.str.title()
                    else:
                        continue
                    diff = (non_nulls != transformed).sum()
                    if diff > 0:
                        working_df.loc[non_nulls.index, col] = transformed
                        self._record_step(
                            operation="casing_standardization",
                            target_column=col,
                            parameters={"case_type": case_type},
                            rows_affected=int(diff),
                            details=f"Standardized casing to '{case_type}' for {diff:,} values in '{col}'.",
                        )

        if categorical_mappings:
            for col, mapping in categorical_mappings.items():
                if col in working_df.columns:
                    mask = working_df[col].isin(mapping.keys())
                    count = int(mask.sum())
                    if count > 0:
                        working_df[col] = working_df[col].replace(mapping)
                        self._record_step(
                            operation="categorical_mapping",
                            target_column=col,
                            parameters={"mapping": mapping},
                            rows_affected=count,
                            details=f"Mapped {count:,} values in '{col}' to standardized categories.",
                        )

        # Step 4: Date Normalization
        if date_columns:
            for col in date_columns:
                if col in working_df.columns:
                    parsed = pd.to_datetime(working_df[col], errors="coerce", format="mixed")
                    # Count how many non-null values were converted
                    valid_before = working_df[col].notna().sum()
                    working_df[col] = parsed.dt.strftime("%Y-%m-%d")
                    self._record_step(
                        operation="date_normalization",
                        target_column=col,
                        parameters={"format": "%Y-%m-%d"},
                        rows_affected=int(valid_before),
                        details=f"Normalized {valid_before:,} dates in '{col}' to ISO-8601 (YYYY-MM-DD).",
                    )

        # Step 5: Range Enforcement (Clamp or Nullify)
        if range_rules:
            for col, bounds in range_rules.items():
                if col in working_df.columns and pd.api.types.is_numeric_dtype(working_df[col]):
                    min_val = bounds.get("min")
                    max_val = bounds.get("max")
                    action = bounds.get("action", "clamp")  # 'clamp' or 'nullify'

                    series = working_df[col].dropna()
                    out_of_bounds = pd.Series(False, index=series.index)
                    if min_val is not None:
                        out_of_bounds |= series < min_val
                    if max_val is not None:
                        out_of_bounds |= series > max_val

                    affected = int(out_of_bounds.sum())
                    if affected > 0:
                        if action == "nullify":
                            working_df.loc[out_of_bounds[out_of_bounds].index, col] = np.nan
                        else:  # clamp
                            working_df[col] = working_df[col].clip(lower=min_val, upper=max_val)
                        self._record_step(
                            operation="range_enforcement",
                            target_column=col,
                            parameters=bounds,
                            rows_affected=affected,
                            details=f"Applied range rule ({action}) to {affected:,} values in '{col}'.",
                        )

        # Step 6: Duplicate Removal
        if drop_duplicates_subset is not None:
            before_rows = len(working_df)
            if drop_duplicates_subset is True:
                working_df = working_df.drop_duplicates(keep="first")
            elif isinstance(drop_duplicates_subset, list):
                working_df = working_df.drop_duplicates(subset=drop_duplicates_subset, keep="first")
            dups_removed = before_rows - len(working_df)
            if dups_removed > 0:
                self._record_step(
                    operation="drop_duplicates",
                    target_column=None,
                    parameters={"subset": drop_duplicates_subset},
                    rows_affected=dups_removed,
                    details=f"Removed {dups_removed:,} duplicate records (kept first occurrence).",
                )

        # Step 7: Missing-Value Handling
        if missing_strategies:
            for col, strat in missing_strategies.items():
                if col not in working_df.columns:
                    continue

                method = strat.get("strategy", "constant").lower()
                fill_val = strat.get("value")
                null_mask = working_df[col].isna()
                null_count = int(null_mask.sum())

                if null_count == 0:
                    continue

                if method == "drop":
                    working_df = working_df.dropna(subset=[col])
                    self._record_step(
                        operation="drop_missing",
                        target_column=col,
                        parameters=strat,
                        rows_affected=null_count,
                        details=f"Dropped {null_count:,} rows with missing values in '{col}'.",
                    )
                elif method == "mean" and pd.api.types.is_numeric_dtype(working_df[col]):
                    val = working_df[col].mean()
                    working_df[col] = working_df[col].fillna(val)
                    self._record_step(
                        operation="fill_mean",
                        target_column=col,
                        parameters={"computed_mean": round(float(val), 4)},
                        rows_affected=null_count,
                        details=f"Imputed {null_count:,} missing values in '{col}' with mean ({val:.2f}).",
                    )
                elif method == "median" and pd.api.types.is_numeric_dtype(working_df[col]):
                    val = working_df[col].median()
                    working_df[col] = working_df[col].fillna(val)
                    self._record_step(
                        operation="fill_median",
                        target_column=col,
                        parameters={"computed_median": round(float(val), 4)},
                        rows_affected=null_count,
                        details=f"Imputed {null_count:,} missing values in '{col}' with median ({val:.2f}).",
                    )
                elif method == "mode":
                    mode_series = working_df[col].mode()
                    if not mode_series.empty:
                        val = mode_series.iloc[0]
                        working_df[col] = working_df[col].fillna(val)
                        self._record_step(
                            operation="fill_mode",
                            target_column=col,
                            parameters={"computed_mode": str(val)},
                            rows_affected=null_count,
                            details=f"Imputed {null_count:,} missing values in '{col}' with mode ('{val}').",
                        )
                elif method == "constant" and fill_val is not None:
                    working_df[col] = working_df[col].fillna(fill_val)
                    self._record_step(
                        operation="fill_constant",
                        target_column=col,
                        parameters={"value": fill_val},
                        rows_affected=null_count,
                        details=f"Imputed {null_count:,} missing values in '{col}' with constant '{fill_val}'.",
                    )
                elif method == "ffill":
                    working_df[col] = working_df[col].ffill()
                    self._record_step(
                        operation="forward_fill",
                        target_column=col,
                        parameters={},
                        rows_affected=null_count,
                        details=f"Forward-filled {null_count:,} missing values in '{col}'.",
                    )
                elif method == "bfill":
                    working_df[col] = working_df[col].bfill()
                    self._record_step(
                        operation="backward_fill",
                        target_column=col,
                        parameters={},
                        rows_affected=null_count,
                        details=f"Backward-filled {null_count:,} missing values in '{col}'.",
                    )

        # Step 8: Strict Type Conversions
        if type_conversions:
            for col, target_type in type_conversions.items():
                if col not in working_df.columns:
                    continue
                try:
                    if target_type.lower() in ("int", "int64", "integer"):
                        # Use pandas nullable integer type Int64
                        working_df[col] = pd.to_numeric(working_df[col], errors="coerce").astype("Int64")
                    elif target_type.lower() in ("float", "float64"):
                        working_df[col] = pd.to_numeric(working_df[col], errors="coerce").astype(float)
                    elif target_type.lower() in ("str", "string"):
                        working_df[col] = working_df[col].astype(str)
                    elif target_type.lower() in ("datetime", "date"):
                        working_df[col] = pd.to_datetime(working_df[col], errors="coerce")

                    self._record_step(
                        operation="type_conversion",
                        target_column=col,
                        parameters={"target_type": target_type},
                        rows_affected=len(working_df),
                        details=f"Casted column '{col}' to strict type '{target_type}'.",
                    )
                except Exception:
                    pass

        # Capture after statistics and compute delta
        after_stats = self._calc_stats(working_df)
        delta = {
            "rows_removed": before_stats["total_rows"] - after_stats["total_rows"],
            "missing_cells_resolved": before_stats["missing_cells"] - after_stats["missing_cells"],
            "duplicates_removed": before_stats["duplicate_rows"] - after_stats["duplicate_rows"],
            "total_operations": len(self.steps),
        }

        return CleaningResult(
            cleaned_df=working_df,
            steps=self.steps,
            before_stats=before_stats,
            after_stats=after_stats,
            delta=delta,
        )

    def _record_step(
        self,
        operation: str,
        target_column: Optional[str],
        parameters: Dict[str, Any],
        rows_affected: int,
        details: str,
    ) -> None:
        step = CleaningStep(
            step_number=len(self.steps) + 1,
            operation=operation,
            target_column=target_column,
            parameters=parameters,
            rows_affected=rows_affected,
            details=details,
        )
        self.steps.append(step)

    def _calc_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        rows = len(df)
        cols = len(df.columns)
        total_cells = df.size
        missing = int(df.isna().sum().sum())
        duplicates = int(df.duplicated().sum()) if rows > 0 else 0
        missing_pct = round((missing / total_cells * 100), 2) if total_cells > 0 else 0.0

        return {
            "total_rows": rows,
            "total_columns": cols,
            "total_cells": total_cells,
            "missing_cells": missing,
            "missing_percentage": missing_pct,
            "duplicate_rows": duplicates,
        }
