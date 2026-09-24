"""Security & Reliability Tests (Phase 11 — V11.0 to V11.5).

Verifies platform defense mechanisms:
- V11.0: File validation & magic byte checks (blocking disguised binaries/executables)
- V11.1: Upload safety & path traversal prevention
- V11.2: API authorization & IDOR (Insecure Direct Object Reference) prevention
- V11.3: CSV formula injection defense
- V11.5: Error handling & non-leakage of server paths
"""

import io
from pathlib import Path
import pytest
from rest_framework.test import APIClient

from src.cleaner import DataCleaningEngine


@pytest.fixture
def client():
    """Provides a DRF APIClient."""
    return APIClient()


def test_magic_byte_binary_pe_disguised_as_csv_rejected(client):
    """Verify Windows executable binary (.exe with MZ header) renamed to .csv is rejected."""
    # MZ header signature (DOS/PE executable)
    fake_exe_content = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00"
    file = io.BytesIO(fake_exe_content)
    file.name = "payload.csv"

    response = client.post("/api/datasets/", {"file": file}, format="multipart")
    assert response.status_code == 400
    assert "Executable binaries" in response.json()["error"]


def test_magic_byte_binary_elf_disguised_as_csv_rejected(client):
    """Verify Linux ELF binary renamed to .csv is rejected."""
    # ELF header signature
    fake_elf_content = b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    file = io.BytesIO(fake_elf_content)
    file.name = "linux_binary.csv"

    response = client.post("/api/datasets/", {"file": file}, format="multipart")
    assert response.status_code == 400
    assert "Linux ELF binaries" in response.json()["error"]



def test_magic_byte_corrupted_xlsx_rejected(client):
    """Verify plain text uploaded with .xlsx extension (missing PK zip header) is rejected."""
    plain_text = b"This is just plain text, not a real zipped xlsx spreadsheet."
    file = io.BytesIO(plain_text)
    file.name = "corrupt.xlsx"

    response = client.post("/api/datasets/", {"file": file}, format="multipart")
    assert response.status_code == 400
    assert "Invalid Excel XLSX file" in response.json()["error"]


def test_path_traversal_filename_sanitized(client):
    """Verify directory traversal patterns like ../../ are stripped from filename."""
    csv_content = b"id,val\n1,100\n2,200\n"
    file = io.BytesIO(csv_content)
    file.name = "../../../etc/passwd.csv"

    response = client.post("/api/datasets/", {"file": file}, format="multipart")
    assert response.status_code == 201
    data = response.json()
    saved_filename = data["dataset"]["original_filename"]

    # Traversal markers must be stripped; only basename remains
    assert ".." not in saved_filename
    assert "/" not in saved_filename
    assert "\\" not in saved_filename
    assert saved_filename == "passwd.csv"


def test_idor_prevention_unauthorized_user_forbidden(client):
    """Verify User B cannot view, profile, clean, or export User A's dataset (IDOR prevention)."""
    csv_content = b"id,secret\n1,private_data\n"
    file = io.BytesIO(csv_content)
    file.name = "confidential.csv"

    # User A uploads dataset
    upload_res = client.post(
        "/api/datasets/",
        {"file": file, "name": "User A Private Data"},
        format="multipart",
        HTTP_X_USER_ID="user_alice_123",
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset"]["id"]

    # User B attempts to access detail endpoint
    detail_res = client.get(
        f"/api/datasets/{dataset_id}/",
        HTTP_X_USER_ID="user_bob_456",
    )
    assert detail_res.status_code == 403
    assert "Access denied" in detail_res.json()["error"]

    # User B attempts to access profile endpoint
    prof_res = client.get(
        f"/api/datasets/{dataset_id}/profile/",
        HTTP_X_USER_ID="user_bob_456",
    )
    assert prof_res.status_code == 403

    # User B attempts to access quality endpoint
    qual_res = client.get(
        f"/api/datasets/{dataset_id}/quality/",
        HTTP_X_USER_ID="user_bob_456",
    )
    assert qual_res.status_code == 403

    # User B attempts to clean User A's dataset
    clean_res = client.post(
        f"/api/datasets/{dataset_id}/clean/",
        {"strip_whitespace": True},
        format="json",
        HTTP_X_USER_ID="user_bob_456",
    )
    assert clean_res.status_code == 403

    # User B attempts to export User A's dataset
    export_res = client.get(
        f"/api/datasets/{dataset_id}/export/",
        HTTP_X_USER_ID="user_bob_456",
    )
    assert export_res.status_code == 403


def test_idor_owner_allowed(client):
    """Verify owner User A with matching X-User-ID header can access their own dataset."""
    csv_content = b"id,metric\n1,500\n"
    file = io.BytesIO(csv_content)
    file.name = "metric.csv"

    upload_res = client.post(
        "/api/datasets/",
        {"file": file},
        format="multipart",
        HTTP_X_USER_ID="user_alice_123",
    )
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset"]["id"]

    # User A accesses detail
    detail_res = client.get(
        f"/api/datasets/{dataset_id}/",
        HTTP_X_USER_ID="user_alice_123",
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["dataset"]["id"] == dataset_id


def test_csv_formula_injection_defense_all_triggers(client):
    """Verify all spreadsheet formula injection triggers (=, +, -, @, \\t, \\r) are neutralized."""
    csv_content = (
        b"formula_test\n"
        b"\"=CMD('calc.exe')\"\n"
        b'"+SUM(1,2)"\n'
        b'"-AVERAGE(A1:A10)"\n'
        b'"@EXECUTE"\n'
        b"\"\tTAB_INJECT\"\n"
        b"\"\rRETURN_INJECT\"\n"
        b"Normal Value\n"
    )
    file = io.BytesIO(csv_content)
    file.name = "injection.csv"

    upload_res = client.post("/api/datasets/", {"file": file}, format="multipart")
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset"]["id"]

    export_res = client.get(f"/api/datasets/{dataset_id}/export/")
    assert export_res.status_code == 200
    content = export_res.content.decode("utf-8")

    # Every formula trigger must be escaped with prepended single quote
    assert "'=CMD('calc.exe')" in content
    assert "'+SUM(1,2)" in content
    assert "'-AVERAGE(A1:A10)" in content
    assert "'@EXECUTE" in content
    assert "'\tTAB_INJECT" in content
    assert "'\rRETURN_INJECT" in content
    assert "Normal Value" in content
    assert "'Normal Value" not in content  # Plain text is left alone

