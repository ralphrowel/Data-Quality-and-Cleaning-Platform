"""Automated API Tests for Django REST Framework endpoints (Phase 7)."""

import io
import json
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    """Provides a DRF APIClient."""
    return APIClient()


def test_health_check_endpoint(client):
    """Verify GET /api/health/ returns 200 OK."""
    response = client.get("/api/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_swagger_and_openapi_endpoints(client):
    """Verify Swagger UI and OpenAPI 3.0 schema endpoints."""
    # Test OpenAPI 3.0 YAML/JSON Schema endpoint
    schema_res = client.get("/api/schema/")
    assert schema_res.status_code == 200
    assert "openapi" in schema_res.content.decode("utf-8").lower() or "paths" in schema_res.content.decode("utf-8").lower()

    # Test Swagger UI documentation HTML endpoint
    docs_res = client.get("/api/docs/")
    assert docs_res.status_code == 200
    assert "swagger" in docs_res.content.decode("utf-8").lower()

    # Test Redoc documentation HTML endpoint
    redoc_res = client.get("/api/redoc/")
    assert redoc_res.status_code == 200
    assert "redoc" in redoc_res.content.decode("utf-8").lower()



def test_dataset_upload_profile_and_score(client):
    """Verify POST /api/datasets/ handles upload, profiles, and generates Version 1."""
    csv_content = b"id,name,age\n1,Alice,25\n2,Bob,30\n3,Charlie,\n"
    file = io.BytesIO(csv_content)
    file.name = "users.csv"

    response = client.post(
        "/api/datasets/",
        {"file": file, "name": "Users List", "description": "Test dataset"},
        format="multipart",
    )

    assert response.status_code == 201
    data = response.json()
    assert "dataset" in data
    assert "version" in data
    assert "quality_score" in data
    assert data["dataset"]["name"] == "Users List"
    assert data["version"]["version_number"] == 1
    assert data["quality_score"]["overall_score"] > 0

    dataset_id = data["dataset"]["id"]

    # Verify listing includes newly created dataset
    list_res = client.get("/api/datasets/")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert any(d["id"] == dataset_id for d in list_data["results"])

    # Verify detail endpoint
    detail_res = client.get(f"/api/datasets/{dataset_id}/")
    assert detail_res.status_code == 200
    assert detail_res.json()["total_versions"] == 1

    # Verify profile endpoint
    prof_res = client.get(f"/api/datasets/{dataset_id}/profile/")
    assert prof_res.status_code == 200
    assert prof_res.json()["summary"]["total_rows"] == 3

    # Verify quality endpoint
    qual_res = client.get(f"/api/datasets/{dataset_id}/quality/")
    assert qual_res.status_code == 200
    assert "quality_report" in qual_res.json()


def test_dataset_upload_invalid_type(client):
    """Verify uploading an unsupported file type returns 400 Bad Request."""
    file = io.BytesIO(b"dummy binary data")
    file.name = "malicious_script.exe"

    response = client.post(
        "/api/datasets/",
        {"file": file},
        format="multipart",
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["error"]


def test_dataset_cleaning_and_versioning(client):
    """Verify POST /api/datasets/{id}/clean/ creates Version 2 and records delta."""
    csv_content = b"id,email,score\n1,  alice@test.com  ,90\n2,bob@test.com,100\n3,,80\n"
    file = io.BytesIO(csv_content)
    file.name = "test_clean.csv"

    upload_res = client.post(
        "/api/datasets/",
        {"file": file, "name": "Cleaning Test"},
        format="multipart",
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset"]["id"]

    # Execute cleaning operation
    clean_payload = {
        "strip_whitespace": True,
        "missing_strategies": {
            "email": {"strategy": "constant", "value": "unknown@test.com"}
        },
    }
    clean_res = client.post(
        f"/api/datasets/{dataset_id}/clean/",
        clean_payload,
        format="json",
    )

    assert clean_res.status_code == 201
    clean_data = clean_res.json()
    assert clean_data["new_version"]["version_number"] == 2
    assert "cleaning_job_id" in clean_data
    assert clean_data["operations_executed"] >= 1

    # Verify versions count in detail
    detail_res = client.get(f"/api/datasets/{dataset_id}/")
    assert detail_res.json()["total_versions"] == 2


def test_dataset_safe_csv_export(client):
    """Verify GET /api/datasets/{id}/export/ neutralizes formula triggers."""
    csv_content = b"title,formula\nNormal,normal\nExploit,=1+1\n"
    file = io.BytesIO(csv_content)
    file.name = "export_test.csv"

    upload_res = client.post(
        "/api/datasets/",
        {"file": file, "name": "Export Test"},
        format="multipart",
    )
    dataset_id = upload_res.json()["dataset"]["id"]

    export_res = client.get(f"/api/datasets/{dataset_id}/export/")
    assert export_res.status_code == 200
    assert export_res["Content-Type"] == "text/csv"

    content = export_res.content.decode("utf-8")
    assert "'=1+1" in content  # Prepend quote formula injection protection


def test_non_existent_dataset_not_found(client):
    """Verify requesting non-existent dataset returns 404."""
    response = client.get("/api/datasets/fake-uuid-not-found/")
    assert response.status_code == 404
