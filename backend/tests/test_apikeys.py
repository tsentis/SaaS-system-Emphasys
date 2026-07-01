"""API key management + API-key-authenticated integration endpoints."""

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


def _seed_project(client, token, acronym="PROJ"):
    from app.ai.extractor import get_extractor
    from app.main import app

    class _E:
        def extract(self, text):
            return ExtractedProject(acronym=acronym, title="Title", confidence=0.8)

    app.dependency_overrides[get_extractor] = lambda: _E()
    up = client.post(
        "/api/v1/documents", headers=_auth(token),
        files={"file": ("p.pdf", _pdf(), "application/pdf")},
    ).json()["document"]["id"]
    client.post(f"/api/v1/projects/from-document/{up}", headers=_auth(token))


def _make_key(client, token, name="ci") -> str:
    r = client.post("/api/v1/api-keys", headers=_auth(token), json={"name": name})
    assert r.status_code == 201, r.text
    return r.json()["key"]


def test_create_key_returns_raw_once(client) -> None:
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    r = client.post("/api/v1/api-keys", headers=_auth(token), json={"name": "ci"})
    assert r.status_code == 201
    assert r.json()["key"].startswith("emph_")
    # Listing never exposes the raw key.
    listed = client.get("/api/v1/api-keys", headers=_auth(token)).json()
    assert len(listed) == 1
    assert "key" not in listed[0]


def test_api_key_accesses_integration_endpoint(client) -> None:
    token = _register(client, "Acme Org", "admin@acme.io")
    _seed_project(client, token)
    key = _make_key(client, token)

    r = client.get("/api/v1/integrations/projects", headers={"X-API-Key": key})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_missing_and_invalid_key_rejected(client) -> None:
    assert client.get("/api/v1/integrations/projects").status_code == 401
    assert client.get(
        "/api/v1/integrations/projects", headers={"X-API-Key": "emph_bogus"}
    ).status_code == 401


def test_revoked_key_rejected(client) -> None:
    token = _register(client, "Beta Org", "admin@beta.io")
    r = client.post("/api/v1/api-keys", headers=_auth(token), json={"name": "temp"})
    key_id = r.json()["id"]
    key = r.json()["key"]
    assert client.get("/api/v1/integrations/projects", headers={"X-API-Key": key}).status_code == 200

    assert client.delete(f"/api/v1/api-keys/{key_id}", headers=_auth(token)).status_code == 204
    assert client.get("/api/v1/integrations/projects", headers={"X-API-Key": key}).status_code == 401


def test_non_admin_cannot_manage_keys(client) -> None:
    admin = _register(client, "Gamma Org", "admin@gamma.io")
    client.post(
        "/api/v1/users", headers=_auth(admin),
        json={"email": "an@gamma.io", "password": "password123", "role": "analyst"},
    )
    analyst = client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "gamma-org", "email": "an@gamma.io", "password": "password123"},
    ).json()["access_token"]
    assert client.post("/api/v1/api-keys", headers=_auth(analyst), json={"name": "x"}).status_code == 403


def test_key_scoped_to_its_tenant(client) -> None:
    token_a = _register(client, "Org One", "a@one-corp.io")
    token_b = _register(client, "Org Two", "b@two-corp.io")
    _seed_project(client, token_a, acronym="AONLY")
    key_a = _make_key(client, token_a)

    projects = client.get("/api/v1/integrations/projects", headers={"X-API-Key": key_a}).json()
    assert len(projects) == 1
    assert projects[0]["acronym"] == "AONLY"
    # Tenant B has no projects; its own key would see none.
    key_b = _make_key(client, token_b)
    assert client.get("/api/v1/integrations/projects", headers={"X-API-Key": key_b}).json() == []
