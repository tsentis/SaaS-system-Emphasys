"""Keyword/faceted search and pgvector semantic search tests."""

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


def _register(client, org: str, email: str) -> str:
    r = client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": "password123"},
    )
    return r.json()["access_token"]


def _auth(t: str) -> dict:
    return {"Authorization": f"Bearer {t}"}


def _install(project: ExtractedProject):
    from app.ai.extractor import get_extractor
    from app.main import app

    class _E:
        def extract(self, text: str) -> ExtractedProject:
            return project

    app.dependency_overrides[get_extractor] = lambda: _E()


def _analyze(client, token, project: ExtractedProject, pages: int) -> str:
    _install(project)
    up = client.post(
        "/api/v1/documents",
        headers=_auth(token),
        files={"file": (f"p{pages}.pdf", _pdf(pages), "application/pdf")},
    ).json()["document"]["id"]
    return client.post(
        f"/api/v1/projects/from-document/{up}", headers=_auth(token)
    ).json()["id"]


def test_keyword_search(client) -> None:
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    _analyze(client, token, ExtractedProject(title="Green Skills Academy", summary="climate education", confidence=0.7), 1)

    hit = client.get("/api/v1/search/projects?q=climate", headers=_auth(token)).json()
    assert len(hit) == 1
    miss = client.get("/api/v1/search/projects?q=zzznotfound", headers=_auth(token)).json()
    assert miss == []


def test_filter_by_country(client) -> None:
    token = _register(client, "Acme Org", "admin@acme.io")
    _analyze(client, token, ExtractedProject(
        acronym="CY1", confidence=0.7,
        partners=[ExtractedPartner(legal_name="Cyprus Uni", country="CY")],
    ), 1)

    assert len(client.get("/api/v1/search/projects?country=CY", headers=_auth(token)).json()) == 1
    assert client.get("/api/v1/search/projects?country=EL", headers=_auth(token)).json() == []


def test_filter_by_status(client) -> None:
    token = _register(client, "Beta Org", "admin@beta.io")
    _analyze(client, token, ExtractedProject(acronym="ST", confidence=0.7), 1)
    assert len(client.get("/api/v1/search/projects?status=extracted", headers=_auth(token)).json()) == 1
    assert client.get("/api/v1/search/projects?status=draft", headers=_auth(token)).json() == []


def test_semantic_search_ranks_closest_first(client) -> None:
    token = _register(client, "Gamma Org", "admin@gamma.io")
    p1 = _analyze(client, token, ExtractedProject(summary="climate education programme", confidence=0.7), 1)
    _analyze(client, token, ExtractedProject(summary="digital health innovation", confidence=0.7), 2)

    results = client.get(
        "/api/v1/search/semantic?q=climate education programme", headers=_auth(token)
    ).json()
    assert len(results) == 2
    assert results[0]["id"] == p1


def test_search_isolated_between_tenants(client) -> None:
    token_a = _register(client, "Org One", "a@one-corp.io")
    token_b = _register(client, "Org Two", "b@two-corp.io")
    _analyze(client, token_a, ExtractedProject(title="Secret Project", summary="hidden", confidence=0.7), 1)

    assert client.get("/api/v1/search/projects?q=Secret", headers=_auth(token_b)).json() == []
    assert client.get("/api/v1/search/semantic?q=hidden", headers=_auth(token_b)).json() == []
