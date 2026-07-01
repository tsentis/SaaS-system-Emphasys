"""Organization registry, fuzzy entity resolution, and merge tests."""

import io

from pypdf import PdfWriter

from app.ai.schemas import ExtractedPartner, ExtractedProject
from app.services.org_resolution import normalize_key, resolve_organization


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


def test_normalize_key_strips_suffixes() -> None:
    assert normalize_key("Acme University Ltd.") == normalize_key("acme university")
    assert normalize_key("Beta GmbH") == "beta"


class _PartnersExtractor:
    """Returns a fixed partner set so we can assert resolution behaviour."""

    def __init__(self, partners):
        self._partners = partners

    def extract(self, text: str) -> ExtractedProject:
        return ExtractedProject(acronym="X", confidence=0.8, partners=self._partners)


def _install_extractor(partners):
    from app.ai.extractor import get_extractor
    from app.main import app

    app.dependency_overrides[get_extractor] = lambda: _PartnersExtractor(partners)


def _upload(client, token, data, name="p.pdf") -> str:
    r = client.post(
        "/api/v1/documents",
        headers=_auth(token),
        files={"file": (name, data, "application/pdf")},
    )
    return r.json()["document"]["id"]


def test_fuzzy_resolution_merges_typo_variants(client) -> None:
    # First project introduces "European Digital Institute".
    _install_extractor([ExtractedPartner(legal_name="European Digital Institute", country="BE")])
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    client.post(f"/api/v1/projects/from-document/{_upload(client, token, _pdf(1))}", headers=_auth(token))

    # Second project has a typo'd variant — should resolve to the same org.
    _install_extractor([ExtractedPartner(legal_name="European Digital Instidute", country="BE")])
    client.post(f"/api/v1/projects/from-document/{_upload(client, token, _pdf(2))}", headers=_auth(token))

    orgs = client.get("/api/v1/organizations", headers=_auth(token)).json()
    assert len(orgs) == 1


def test_organization_detail_lists_projects(client) -> None:
    _install_extractor([ExtractedPartner(legal_name="Acme University", role="coordinator")])
    token = _register(client, "Acme Org", "admin@acme.io")
    client.post(f"/api/v1/projects/from-document/{_upload(client, token, _pdf(1))}", headers=_auth(token))

    org_id = client.get("/api/v1/organizations", headers=_auth(token)).json()[0]["id"]
    detail = client.get(f"/api/v1/organizations/{org_id}", headers=_auth(token)).json()
    assert len(detail["projects"]) == 1
    assert detail["projects"][0]["role"] == "coordinator"


def test_list_filters_by_country(client) -> None:
    _install_extractor([
        ExtractedPartner(legal_name="Org Alpha", country="CY"),
        ExtractedPartner(legal_name="Org Beta", country="EL"),
    ])
    token = _register(client, "Filter Org", "admin@filter.io")
    client.post(f"/api/v1/projects/from-document/{_upload(client, token, _pdf(1))}", headers=_auth(token))

    cy = client.get("/api/v1/organizations?country=CY", headers=_auth(token)).json()
    assert {o["legal_name"] for o in cy} == {"Org Alpha"}


def test_merge_organizations(client) -> None:
    _install_extractor([
        ExtractedPartner(legal_name="Uni A", role="coordinator"),
        ExtractedPartner(legal_name="Completely Different Name", role="partner"),
    ])
    token = _register(client, "Merge Org", "admin@merge.io")
    client.post(f"/api/v1/projects/from-document/{_upload(client, token, _pdf(1))}", headers=_auth(token))

    orgs = client.get("/api/v1/organizations", headers=_auth(token)).json()
    keep = next(o for o in orgs if o["legal_name"] == "Uni A")
    dup = next(o for o in orgs if o["legal_name"] == "Completely Different Name")

    resp = client.post(
        f"/api/v1/organizations/{keep['id']}/merge",
        headers=_auth(token),
        json={"duplicate_id": dup["id"]},
    )
    assert resp.status_code == 200, resp.text
    # Keep now carries both partner roles' projects; duplicate is gone.
    assert len(client.get("/api/v1/organizations", headers=_auth(token)).json()) == 1
    assert client.get(f"/api/v1/organizations/{dup['id']}", headers=_auth(token)).status_code == 404


def test_organizations_isolated_between_tenants(client) -> None:
    _install_extractor([ExtractedPartner(legal_name="Secret Org", country="CY")])
    token_a = _register(client, "Org One", "a@one-corp.io")
    token_b = _register(client, "Org Two", "b@two-corp.io")
    client.post(f"/api/v1/projects/from-document/{_upload(client, token_a, _pdf(1))}", headers=_auth(token_a))

    assert client.get("/api/v1/organizations", headers=_auth(token_b)).json() == []
