"""REST API Views for Data Quality & Cleaning Platform.

Phase 7: V7.1 – V7.6
Provides endpoints for:
- Dataset upload, profiling, and quality scorecard generation
- Dataset listing and version history retrieval
- Executing deterministic cleaning operations and lineage tracking
- Safe CSV export with formula injection prevention
"""

import io
from pathlib import Path
import re
from typing import Any, Dict
from django.http import HttpResponse, JsonResponse
import pandas as pd
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from src.cleaner import DataCleaningEngine
from src.profiler import DataProfiler
from src.quality import DataQualityEngine
from src.repository import DatasetRepository
from src.scorer import DataQualityScorer

# Shared singleton services
repo = DatasetRepository(db_path="data/platform.db")
profiler = DataProfiler()
quality_engine = DataQualityEngine()
scorer = DataQualityScorer()
cleaner = DataCleaningEngine()


@api_view(["GET"])
def health_check(request):
    """Simple API liveness healthcheck."""
    return Response(
        {
            "status": "healthy",
            "service": "Data Quality & Cleaning Platform API",
            "version": "1.0.0",
        }
    )


@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def datasets_collection(request):
    """GET: List all datasets with their latest quality scores.

    POST: Upload a CSV/Excel file, create dataset & Version 1, profile and score it.
    """
    if request.method == "GET":
        user_id = request.headers.get("X-User-ID", "default_user")
        with repo._connection() as conn:
            cursor = conn.execute(
                """
                SELECT d.*,
                       COUNT(v.id) AS total_versions,
                       MAX(v.version_number) AS latest_version_number,
                       (SELECT qr.overall_score
                        FROM dataset_versions v2
                        JOIN quality_reports qr ON v2.id = qr.version_id
                        WHERE v2.dataset_id = d.id
                        ORDER BY v2.version_number DESC LIMIT 1) AS latest_quality_score,
                       (SELECT qr.grade
                        FROM dataset_versions v2
                        JOIN quality_reports qr ON v2.id = qr.version_id
                        WHERE v2.dataset_id = d.id
                        ORDER BY v2.version_number DESC LIMIT 1) AS latest_grade
                FROM datasets d
                LEFT JOIN dataset_versions v ON d.id = v.dataset_id
                GROUP BY d.id
                ORDER BY d.created_at DESC
                """
            )
            rows = [dict(row) for row in cursor.fetchall()]
        return Response({"count": len(rows), "results": rows})

    # POST: Upload and process dataset
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return Response({"error": "No file uploaded. Key 'file' is required."}, status=status.HTTP_400_BAD_REQUEST)

    # Validate file size (<= 25 MB)
    if uploaded_file.size > 26214400:
        return Response(
            {"error": "File exceeds maximum upload size of 25 MB."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Validate file extension
    filename = uploaded_file.name
    ext = Path(filename).suffix.lower()
    if ext not in (".csv", ".xlsx", ".xls"):
        return Response(
            {"error": f"Unsupported file type '{ext}'. Allowed: .csv, .xlsx, .xls"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    dataset_name = request.data.get("name", Path(filename).stem.replace("_", " ").title())
    description = request.data.get("description", "")
    user_id = request.headers.get("X-User-ID", request.data.get("user_id", "default_user"))

    try:
        if ext == ".csv":
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        return Response({"error": f"Failed to parse file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Register Dataset
    dataset = repo.create_dataset(
        name=dataset_name,
        original_filename=filename,
        description=description,
        user_id=user_id,
    )

    # 2. Create Version 1 (Parquet snapshot on disk)
    v1 = repo.create_version(dataset.id, df, storage_dir="data/storage")

    # 3. Profile & Quality Evaluation
    profile_res = profiler.profile(df)
    quality_rep = quality_engine.analyze(df)
    score_res = scorer.score(df, existing_report=quality_rep)

    # 4. Save Quality Report in DB
    repo.save_quality_report(v1.id, score_res, quality_rep)

    return Response(
        {
            "message": "Dataset uploaded and profiled successfully.",
            "dataset": dataset.to_dict(),
            "version": v1.to_dict(),
            "profile_summary": profile_res.summary.to_dict(),
            "quality_score": score_res.to_dict(),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def dataset_detail(request, dataset_id):
    """Returns dataset metadata and its version history."""
    dataset = repo.get_dataset(dataset_id)
    if not dataset:
        return Response({"error": f"Dataset '{dataset_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    versions = repo.get_dataset_versions(dataset_id)
    return Response(
        {
            "dataset": dataset,
            "total_versions": len(versions),
            "versions": versions,
        }
    )


@api_view(["GET"])
def dataset_profile(request, dataset_id):
    """Generates and returns structural profile for a dataset version."""
    dataset = repo.get_dataset(dataset_id)
    if not dataset:
        return Response({"error": f"Dataset '{dataset_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    version_id = request.query_params.get("version_id")
    if not version_id:
        versions = repo.get_dataset_versions(dataset_id)
        if not versions:
            return Response({"error": "No versions found for dataset."}, status=status.HTTP_404_NOT_FOUND)
        version_id = versions[-1]["id"]

    try:
        df = repo.load_version_dataframe(version_id)
        profile_res = profiler.profile(df)
        return Response(profile_res.to_dict())
    except Exception as e:
        return Response({"error": f"Failed to profile version: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def dataset_quality(request, dataset_id):
    """Returns quality report and issue breakdown for a dataset version."""
    dataset = repo.get_dataset(dataset_id)
    if not dataset:
        return Response({"error": f"Dataset '{dataset_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    version_id = request.query_params.get("version_id")
    if not version_id:
        versions = repo.get_dataset_versions(dataset_id)
        if not versions:
            return Response({"error": "No versions found for dataset."}, status=status.HTTP_404_NOT_FOUND)
        version_id = versions[-1]["id"]

    with repo._connection() as conn:
        q_row = conn.execute("SELECT * FROM quality_reports WHERE version_id = ?", (version_id,)).fetchone()
        if not q_row:
            return Response({"error": "Quality report not found for this version."}, status=status.HTTP_404_NOT_FOUND)
        q_report = dict(q_row)

        issues_cursor = conn.execute("SELECT * FROM quality_issues WHERE report_id = ?", (q_report["id"],))
        issues = [dict(r) for r in issues_cursor.fetchall()]

    return Response({"quality_report": q_report, "issues_count": len(issues), "issues": issues})


@api_view(["POST"])
def dataset_clean(request, dataset_id):
    """Executes cleaning operations on the latest version, creates a new version,

    and returns the before/after quality delta.
    """
    dataset = repo.get_dataset(dataset_id)
    if not dataset:
        return Response({"error": f"Dataset '{dataset_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    versions = repo.get_dataset_versions(dataset_id)
    if not versions:
        return Response({"error": "No source versions found to clean."}, status=status.HTTP_400_BAD_REQUEST)

    latest_version = versions[-1]
    source_df = repo.load_version_dataframe(latest_version["id"])

    # Parse cleaning configuration parameters from request body
    body: Dict[str, Any] = request.data
    strip_whitespace = body.get("strip_whitespace", True)
    normalize_cols = body.get("normalize_column_names", True)
    casing_rules = body.get("casing_rules")
    cat_mappings = body.get("categorical_mappings")
    date_cols = body.get("date_columns")
    range_rules = body.get("range_rules")
    drop_dups = body.get("drop_duplicates_subset")
    missing_strats = body.get("missing_strategies")

    # 1. Execute Cleaning Pipeline
    clean_result = cleaner.clean(
        source_df,
        strip_whitespace=strip_whitespace,
        normalize_column_names=normalize_cols,
        categorical_mappings=cat_mappings,
        casing_rules=casing_rules,
        date_columns=date_cols,
        range_rules=range_rules,
        drop_duplicates_subset=drop_dups,
        missing_strategies=missing_strats,
    )

    # 2. Persist New Version (Parquet snapshot on disk)
    new_version = repo.create_version(
        dataset_id=dataset_id,
        df=clean_result.cleaned_df,
        storage_dir="data/storage",
        parent_version_id=latest_version["id"],
    )

    # 3. Evaluate New Version Quality
    quality_rep = quality_engine.analyze(clean_result.cleaned_df)
    score_res = scorer.score(clean_result.cleaned_df, existing_report=quality_rep)
    repo.save_quality_report(new_version.id, score_res, quality_rep)

    # 4. Record Lineage Transformation Job
    old_score = float(latest_version.get("overall_score") or 0.0)
    score_delta = round(score_res.overall_score - old_score, 2)
    job = repo.record_cleaning_job(
        source_version_id=latest_version["id"],
        target_version_id=new_version.id,
        cleaning_result=clean_result,
        quality_score_delta=score_delta,
    )

    return Response(
        {
            "message": f"Successfully created Version {new_version.version_number}.",
            "new_version": new_version.to_dict(),
            "cleaning_job_id": job.id,
            "quality_score": score_res.to_dict(),
            "score_delta": score_delta,
            "operations_executed": len(clean_result.steps),
            "summary_delta": clean_result.delta,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def dataset_export(request, dataset_id):
    """Downloads cleaned dataset as safe CSV with formula injection sanitization."""
    dataset = repo.get_dataset(dataset_id)
    if not dataset:
        return Response({"error": f"Dataset '{dataset_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    version_id = request.query_params.get("version_id")
    if not version_id:
        versions = repo.get_dataset_versions(dataset_id)
        if not versions:
            return Response({"error": "No versions found to export."}, status=status.HTTP_404_NOT_FOUND)
        version_id = versions[-1]["id"]

    try:
        df = repo.load_version_dataframe(version_id)

        # Apply formula injection defense
        formula_triggers = re.compile(r"^[\=\+\-\@\t\r]")
        str_cols = df.select_dtypes(include=["object", "str"]).columns
        export_df = df.copy()
        for col in str_cols:
            export_df[col] = export_df[col].apply(
                lambda val: f"'{val}" if isinstance(val, str) and formula_triggers.match(val) else val
            )

        # Generate CSV buffer
        buffer = io.StringIO()
        export_df.to_csv(buffer, index=False, encoding="utf-8")
        buffer.seek(0)

        filename = f"cleaned_{Path(dataset['original_filename']).stem}.csv"
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        return Response({"error": f"Failed to export dataset: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
