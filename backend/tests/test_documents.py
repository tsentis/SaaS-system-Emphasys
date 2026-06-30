"""Integration tests for document upload & management (requires a database)."""

import io

from pypdf import PdfWriter


def _pdf_bytes(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _register(client, org: str, email: str, password: str = "password123") -> str:
    resp = client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _upload(client, token: str, data: bytes, name: str = "proposal.pdf"):
    return client.post(
        "/api/v1/documents",
        headers=_auth(token),
        files={"file": (name, data, "application/pdf")},
    )


def test_upload_pdf(client) -> None:
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    resp = _upload(client, token, _pdf_bytes(2))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["duplicate"] is False
    doc = body["document"]
    assert doc["filename"] == "proposal.pdf"
    assert doc["page_count"] == 2
    assert doc["size_bytes"] > 0
    assert doc["status"] == "uploaded"
    assert len(doc["sha256"]) == 64


def test_duplicate_detected_by_hash(client) -> None:
    token = _register(client, "Acme Org", "admin@acme.io")
    data = _pdf_bytes(1)
    first = _upload(client, token, data).json()
    second = _upload(client, token, data, name="renamed.pdf").json()
    assert second["duplicate"] is True
    assert second["document"]["id"] == first["document"]["id"]

    listing = client.get("/api/v1/documents", headers=_auth(token)).json()
    assert len(listing) == 1


def test_non_pdf_rejected(client) -> None:
    token = _register(client, "Beta Org", "admin@beta.io")
    resp = client.post(
        "/api/v1/documents",
        headers=_auth(token),
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415


def test_download_url(client) -> None:
    token = _register(client, "Gamma Org", "admin@gamma.io")
    doc_id = _upload(client, token, _pdf_bytes()).json()["document"]["id"]
    resp = client.get(f"/api/v1/documents/{doc_id}/download", headers=_auth(token))
    assert resp.status_code == 200
    assert resp.json()["url"].startswith("memory://")
    assert resp.json()["expires_in"] == 3600


def test_soft_delete_hides_document(client) -> None:
    token = _register(client, "Delta Org", "admin@delta.io")
    doc_id = _upload(client, token, _pdf_bytes()).json()["document"]["id"]

    assert client.delete(f"/api/v1/documents/{doc_id}", headers=_auth(token)).status_code == 204
    assert client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token)).status_code == 404
    assert client.get("/api/v1/documents", headers=_auth(token)).json() == []


def test_viewer_cannot_upload(client) -> None:
    admin = _register(client, "Epsilon Org", "admin@epsilon.io")
    client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "viewer@epsilon.io", "password": "password123", "role": "viewer"},
    )
    viewer = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": "epsilon-org",
            "email": "viewer@epsilon.io",
            "password": "password123",
        },
    ).json()["access_token"]
    assert _upload(client, viewer, _pdf_bytes()).status_code == 403


def test_documents_isolated_between_tenants(client) -> None:
    token_a = _register(client, "Org One", "a@one-corp.io")
    token_b = _register(client, "Org Two", "b@two-corp.io")
    doc_id_a = _upload(client, token_a, _pdf_bytes()).json()["document"]["id"]

    # Tenant B cannot list or fetch tenant A's document.
    assert client.get("/api/v1/documents", headers=_auth(token_b)).json() == []
    assert client.get(f"/api/v1/documents/{doc_id_a}", headers=_auth(token_b)).status_code == 404


def test_same_file_distinct_across_tenants(client) -> None:
    """Identical bytes uploaded by two tenants are two separate documents."""
    token_a = _register(client, "Org Three", "a@three-corp.io")
    token_b = _register(client, "Org Four", "b@four-corp.io")
    data = _pdf_bytes(3)

    a = _upload(client, token_a, data).json()
    b = _upload(client, token_b, data).json()
    assert a["duplicate"] is False
    assert b["duplicate"] is False
    assert a["document"]["id"] != b["document"]["id"]