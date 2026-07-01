"""GDPR requests, audit log, and billing plan tests."""

import io
import uuid

from pypdf import PdfWriter
from sqlalchemy import text
from sqlalchemy.orm import Session as SASession

from app.models.organization import Person


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


def _tenant_id(client, token) -> str:
    return client.get("/api/v1/auth/me", headers=_auth(token)).json()["tenant_id"]


def _add_person(engine, tenant_id: str, email: str, name="Jane Subject") -> None:
    with SASession(engine) as s:
        s.add(Person(tenant_id=uuid.UUID(tenant_id), full_name=name, email=email))
        s.commit()


def test_gdpr_erasure(client, engine) -> None:
    token = _register(client, "Emphasys Centre", "admin@emphasys.io")
    tid = _tenant_id(client, token)
    _add_person(engine, tid, "jane@subject.io")

    req = client.post(
        "/api/v1/gdpr/requests",
        headers=_auth(token),
        json={"subject_email": "jane@subject.io", "request_type": "erasure"},
    )
    assert req.status_code == 201, req.text
    result = client.post(
        f"/api/v1/gdpr/requests/{req.json()['id']}/process", headers=_auth(token)
    ).json()
    assert result == {"action": "erasure", "erased_persons": 1}

    with engine.connect() as conn:
        emails = [r[0] for r in conn.execute(text("SELECT email FROM persons"))]
    assert emails == [None]


def test_gdpr_access(client, engine) -> None:
    token = _register(client, "Acme Org", "admin@acme.io")
    tid = _tenant_id(client, token)
    _add_person(engine, tid, "bob@subject.io", name="Bob Subject")

    req = client.post(
        "/api/v1/gdpr/requests",
        headers=_auth(token),
        json={"subject_email": "bob@subject.io", "request_type": "access"},
    ).json()
    result = client.post(
        f"/api/v1/gdpr/requests/{req['id']}/process", headers=_auth(token)
    ).json()
    assert result["action"] == "access"
    assert result["persons"][0]["email"] == "bob@subject.io"


def test_gdpr_invalid_type_rejected(client) -> None:
    token = _register(client, "Beta Org", "admin@beta.io")
    resp = client.post(
        "/api/v1/gdpr/requests",
        headers=_auth(token),
        json={"subject_email": "x@subject.io", "request_type": "sell-data"},
    )
    assert resp.status_code == 422


def test_audit_log_records_upload(client) -> None:
    token = _register(client, "Gamma Org", "admin@gamma.io")
    client.post(
        "/api/v1/documents", headers=_auth(token),
        files={"file": ("p.pdf", _pdf(), "application/pdf")},
    )
    entries = client.get("/api/v1/audit", headers=_auth(token)).json()
    assert any(e["action"] == "document.upload" for e in entries)


def test_billing_plan_get_and_update(client) -> None:
    token = _register(client, "Delta Org", "admin@delta.io")
    assert client.get("/api/v1/billing/plan", headers=_auth(token)).json() == {"plan": "free"}

    updated = client.put(
        "/api/v1/billing/plan", headers=_auth(token), json={"plan": "pro"}
    )
    assert updated.json() == {"plan": "pro"}
    assert client.get("/api/v1/billing/plan", headers=_auth(token)).json() == {"plan": "pro"}


def test_billing_invalid_plan_rejected(client) -> None:
    token = _register(client, "Epsilon Org", "admin@epsilon.io")
    resp = client.put(
        "/api/v1/billing/plan", headers=_auth(token), json={"plan": "unlimited-galaxy"}
    )
    assert resp.status_code == 422


def test_gdpr_requires_admin(client) -> None:
    admin = _register(client, "Zeta Org", "admin@zeta.io")
    client.post(
        "/api/v1/users", headers=_auth(admin),
        json={"email": "an@zeta.io", "password": "password123", "role": "analyst"},
    )
    analyst = client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "zeta-org", "email": "an@zeta.io", "password": "password123"},
    ).json()["access_token"]
    resp = client.post(
        "/api/v1/gdpr/requests",
        headers=_auth(analyst),
        json={"subject_email": "x@subject.io", "request_type": "access"},
    )
    assert resp.status_code == 403
