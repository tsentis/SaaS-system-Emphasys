"""Export endpoint tests: CSV / XLSX / PDF / Word."""

import io

from pypdf import PdfWriter

from app.ai.schemas import ExtractedProject


def _pdf() -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=120, height=120)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def _register(client, org, email):
    return client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": "password123"},
    ).json()["access_token"]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _seed_project(client, token):
    from app.ai.extractor import get_extractor
    from app.main import app

    class _E:
        def extract(self, text):
            return ExtractedProject(
                acronym="GREENFUT",
                title="Green Futures",
                total_budget=250000.0,
                confidence=0.8,
            )

    app.dependency_overrides[get_extractor] = lambda: _E()
    up = client.post(
        "/api/v1/documents", headers=_auth(token),
        files={"file": ("p.pdf", _pdf(), "application/pdf")},
    ).json()["document"]["id"]
    client.post(f"/api/v1/projects/from-document/{up}", headers=_auth(token))


def test_export_csv(client) -> None:
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    _seed_project(client, token)
    r = client.get("/api/v1/export/projects.csv", headers=_auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    body = r.content.decode()
    assert "Acronym" in body
    assert "GREENFUT" in body


def test_export_xlsx(client) -> None:
    token = _register(client, "Acme Org", "admin@acme.io")
    _seed_project(client, token)
    r = client.get("/api/v1/export/projects.xlsx", headers=_auth(token))
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert r.content[:2] == b"PK"  # xlsx is a zip container


def test_export_docx(client) -> None:
    token = _register(client, "Beta Org", "admin@beta.io")
    _seed_project(client, token)
    r = client.get("/api/v1/export/projects.docx", headers=_auth(token))
    assert r.status_code == 200
    assert r.content[:2] == b"PK"  # docx is a zip container


def test_export_pdf(client) -> None:
    token = _register(client, "Gamma Org", "admin@gamma.io")
    _seed_project(client, token)
    r = client.get("/api/v1/export/projects.pdf", headers=_auth(token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"


def test_export_requires_auth(client) -> None:
    assert client.get("/api/v1/export/projects.csv").status_code == 401
