"""External enrichment tests (using a fake source)."""

import io

from pypdf import PdfWriter

from app.ai.schemas import ExtractedProject
from app.enrichment.sources import FakeSource


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


def _use_fake_sources():
    from app.enrichment.sources import get_enrichment_registry
    from app.main import app

    app.dependency_overrides[get_enrichment_registry] = lambda: {
        "cordis": FakeSource("cordis")
    }


def _seed_project(client, token, acronym="GREENFUT") -> str:
    from app.ai.extractor import get_extractor
    from app.main import app

    class _E:
        def extract(self, text):
            return ExtractedProject(acronym=acronym, title="Green Futures", confidence=0.8)

    app.dependency_overrides[get_extractor] = lambda: _E()
    up = client.post(
        "/api/v1/documents", headers=_auth(token),
        files={"file": ("p.pdf", _pdf(), "application/pdf")},
    ).json()["document"]["id"]
    return client.post(
        f"/api/v1/projects/from-document/{up}", headers=_auth(token)
    ).json()["id"]


def test_enrich_and_list(client) -> None:
    _use_fake_sources()
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    pid = _seed_project(client, token)

    resp = client.post(f"/api/v1/projects/{pid}/enrich?source=cordis", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["matched"] is True
    assert body["record"]["source"] == "cordis"
    assert body["record"]["payload"]["records"][0]["title"] == "GREENFUT"

    listing = client.get(f"/api/v1/projects/{pid}/enrichment", headers=_auth(token)).json()
    assert len(listing) == 1


def test_unknown_source_rejected(client) -> None:
    _use_fake_sources()
    token = _register(client, "Acme Org", "admin@acme.io")
    pid = _seed_project(client, token)
    resp = client.post(f"/api/v1/projects/{pid}/enrich?source=bogus", headers=_auth(token))
    assert resp.status_code == 400


def test_viewer_cannot_enrich(client) -> None:
    _use_fake_sources()
    admin = _register(client, "Beta Org", "admin@beta.io")
    pid = _seed_project(client, admin)
    client.post(
        "/api/v1/users", headers=_auth(admin),
        json={"email": "v@beta.io", "password": "password123", "role": "viewer"},
    )
    viewer = client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "beta-org", "email": "v@beta.io", "password": "password123"},
    ).json()["access_token"]
    resp = client.post(f"/api/v1/projects/{pid}/enrich?source=cordis", headers=_auth(viewer))
    assert resp.status_code == 403


def test_enrichment_isolated_between_tenants(client) -> None:
    _use_fake_sources()
    token_a = _register(client, "Org One", "a@one-corp.io")
    token_b = _register(client, "Org Two", "b@two-corp.io")
    pid = _seed_project(client, token_a)
    client.post(f"/api/v1/projects/{pid}/enrich?source=cordis", headers=_auth(token_a))

    # Tenant B cannot see the project or its enrichment.
    assert client.get(f"/api/v1/projects/{pid}/enrichment", headers=_auth(token_b)).json() == []
