"""Extraction pipeline: unit test for the fake extractor + integration tests."""

import io

from pypdf import PdfWriter

from app.ai.extractor import FakeExtractor
from app.ai.schemas import ExtractedPartner, ExtractedProject


def _pdf(pages: int = 1) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=120, height=120)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _register(client, org: str, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": "password123"},
    )
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def _upload(client, token: str, data: bytes, name="proposal.pdf") -> str:
    r = client.post(
        "/api/v1/documents",
        headers=_auth(token),
        files={"file": (name, data, "application/pdf")},
    )
    assert r.status_code == 201, r.text
    return r.json()["document"]["id"]


class _StubExtractor:
    """Deterministic extractor returning a fixed project + two partners."""

    def extract(self, text: str) -> ExtractedProject:
        return ExtractedProject(
            title="Green Futures for Europe",
            acronym="GREENFUT",
            programme="Erasmus+",
            summary="A project about green skills.",
            confidence=0.9,
            partners=[
                ExtractedPartner(
                    legal_name="Acme University", country="CY", role="coordinator"
                ),
                ExtractedPartner(
                    legal_name="Beta NGO", country="EL", role="partner"
                ),
            ],
        )


def _use_stub_extractor():
    from app.ai.extractor import get_extractor
    from app.main import app

    app.dependency_overrides[get_extractor] = lambda: _StubExtractor()


# --- unit ---

def test_fake_extractor_finds_partners() -> None:
    text = (
        "GREENFUTURE\n"
        "Acme University is the project coordinator.\n"
        "Beta NGO participates as a partner.\n"
    )
    result = FakeExtractor().extract(text)
    assert result.acronym == "GREENFUTURE"
    roles = {p.role for p in result.partners}
    assert "coordinator" in roles
    assert "partner" in roles


# --- integration ---

def test_analyze_creates_project(client) -> None:
    _use_stub_extractor()
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    doc_id = _upload(client, token, _pdf())

    resp = client.post(f"/api/v1/projects/from-document/{doc_id}", headers=_auth(token))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["acronym"] == "GREENFUT"
    assert body["status"] == "extracted"
    assert len(body["partners"]) == 2

    assert len(client.get("/api/v1/projects", headers=_auth(token)).json()) == 1
    # The source document is now marked done.
    doc = client.get(f"/api/v1/documents/{doc_id}", headers=_auth(token)).json()
    assert doc["status"] == "done"


def test_partner_deduplicated_across_projects(client) -> None:
    _use_stub_extractor()
    token = _register(client, "Acme Org", "admin@acme.io")
    p1 = client.post(
        f"/api/v1/projects/from-document/{_upload(client, token, _pdf(1))}",
        headers=_auth(token),
    ).json()
    p2 = client.post(
        f"/api/v1/projects/from-document/{_upload(client, token, _pdf(2))}",
        headers=_auth(token),
    ).json()

    def org_id(project, name):
        return next(p["organization_id"] for p in project["partners"] if p["legal_name"] == name)

    # Same partner name resolves to the same organization row.
    assert org_id(p1, "Acme University") == org_id(p2, "Acme University")


def test_viewer_cannot_analyze(client) -> None:
    _use_stub_extractor()
    admin = _register(client, "Beta Org", "admin@beta.io")
    client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "viewer@beta.io", "password": "password123", "role": "viewer"},
    )
    viewer = client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "beta-org", "email": "viewer@beta.io", "password": "password123"},
    ).json()["access_token"]
    doc_id = _upload(client, admin, _pdf())
    resp = client.post(f"/api/v1/projects/from-document/{doc_id}", headers=_auth(viewer))
    assert resp.status_code == 403


def test_projects_isolated_between_tenants(client) -> None:
    _use_stub_extractor()
    token_a = _register(client, "Org One", "a@one-corp.io")
    token_b = _register(client, "Org Two", "b@two-corp.io")
    pid = client.post(
        f"/api/v1/projects/from-document/{_upload(client, token_a, _pdf())}",
        headers=_auth(token_a),
    ).json()["id"]

    assert client.get("/api/v1/projects", headers=_auth(token_b)).json() == []
    assert client.get(f"/api/v1/projects/{pid}", headers=_auth(token_b)).status_code == 404
