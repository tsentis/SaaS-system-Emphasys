"""Analytics endpoint tests."""

import io

from pypdf import PdfWriter

from app.ai.schemas import ExtractedPartner, ExtractedProject


def _pdf(pages: int = 1) -> bytes:
    w = PdfWriter()
    for _ in range(pages):
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


def _analyze(client, token, project: ExtractedProject, pages: int) -> None:
    from app.ai.extractor import get_extractor
    from app.main import app

    class _E:
        def extract(self, text): return project

    app.dependency_overrides[get_extractor] = lambda: _E()
    up = client.post(
        "/api/v1/documents",
        headers=_auth(token),
        files={"file": (f"p{pages}.pdf", _pdf(pages), "application/pdf")},
    ).json()["document"]["id"]
    client.post(f"/api/v1/projects/from-document/{up}", headers=_auth(token))


def test_summary_counts(client) -> None:
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    _analyze(client, token, ExtractedProject(
        acronym="A", programme="Erasmus+", confidence=0.7,
        partners=[ExtractedPartner(legal_name="Uni CY", country="CY")],
    ), 1)

    s = client.get("/api/v1/analytics/summary", headers=_auth(token)).json()
    assert s["projects"] == 1
    assert s["documents"] == 1
    assert s["organizations"] == 1
    assert s["programmes"] == 1
    assert s["partner_countries"] == 1


def test_projects_by_programme(client) -> None:
    token = _register(client, "Acme Org", "admin@acme.io")
    _analyze(client, token, ExtractedProject(acronym="H", programme="Horizon Europe", confidence=0.7), 1)
    _analyze(client, token, ExtractedProject(acronym="H2", programme="Horizon Europe", confidence=0.7), 2)

    rows = client.get("/api/v1/analytics/projects-by-programme", headers=_auth(token)).json()
    assert rows == [{"label": "Horizon Europe", "count": 2}]


def test_organizations_by_country(client) -> None:
    token = _register(client, "Beta Org", "admin@beta.io")
    _analyze(client, token, ExtractedProject(acronym="C", confidence=0.7, partners=[
        ExtractedPartner(legal_name="Org CY", country="CY"),
        ExtractedPartner(legal_name="Org EL", country="EL"),
    ]), 1)

    rows = client.get("/api/v1/analytics/organizations-by-country", headers=_auth(token)).json()
    assert {r["label"] for r in rows} == {"CY", "EL"}


def test_status_and_timeline(client) -> None:
    token = _register(client, "Gamma Org", "admin@gamma.io")
    _analyze(client, token, ExtractedProject(acronym="S", confidence=0.7, start_date="2025-01-01"), 1)

    status = client.get("/api/v1/analytics/status", headers=_auth(token)).json()
    assert status["projects"].get("extracted") == 1
    assert status["documents"].get("done") == 1

    timeline = client.get("/api/v1/analytics/timeline", headers=_auth(token)).json()
    assert {"year": 2025, "count": 1} in timeline


def test_analytics_scoped_to_tenant(client) -> None:
    token_a = _register(client, "Org One", "a@one-corp.io")
    token_b = _register(client, "Org Two", "b@two-corp.io")
    _analyze(client, token_a, ExtractedProject(acronym="X", confidence=0.7), 1)

    assert client.get("/api/v1/analytics/summary", headers=_auth(token_b)).json()["projects"] == 0
