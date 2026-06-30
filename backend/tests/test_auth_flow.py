"""Integration tests for auth, RBAC, and tenant isolation (requires a database)."""


def _register(client, org: str, email: str, password: str = "password123") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={"organization_name": org, "email": email, "password": password},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_tokens(client) -> None:
    body = _register(client, "Emphasys Centre", "admin@emphasys.io")
    assert body["access_token"]
    assert body["refresh_token"]


def test_login_and_me(client) -> None:
    _register(client, "Acme Org", "boss@acme.io")
    login = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": "acme-org",
            "email": "boss@acme.io",
            "password": "password123",
        },
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers=_auth(token))
    assert me.status_code == 200
    assert me.json()["email"] == "boss@acme.io"
    assert "admin" in me.json()["roles"]


def test_wrong_password_rejected(client) -> None:
    _register(client, "Beta Org", "u@beta.io")
    resp = client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "beta-org", "email": "u@beta.io", "password": "nope"},
    )
    assert resp.status_code == 401


def test_admin_can_create_and_list_users(client) -> None:
    token = _register(client, "Gamma Org", "admin@gamma.io")["access_token"]
    created = client.post(
        "/api/v1/users",
        headers=_auth(token),
        json={
            "email": "analyst@gamma.io",
            "password": "password123",
            "role": "analyst",
        },
    )
    assert created.status_code == 201, created.text

    listing = client.get("/api/v1/users", headers=_auth(token))
    assert listing.status_code == 200
    emails = {u["email"] for u in listing.json()}
    assert {"admin@gamma.io", "analyst@gamma.io"} <= emails


def test_viewer_forbidden_from_user_admin(client) -> None:
    admin_token = _register(client, "Delta Org", "admin@delta.io")["access_token"]
    client.post(
        "/api/v1/users",
        headers=_auth(admin_token),
        json={"email": "v@delta.io", "password": "password123", "role": "viewer"},
    )
    viewer_token = client.post(
        "/api/v1/auth/login",
        json={
            "tenant_slug": "delta-org",
            "email": "v@delta.io",
            "password": "password123",
        },
    ).json()["access_token"]

    resp = client.get("/api/v1/users", headers=_auth(viewer_token))
    assert resp.status_code == 403


def test_tenant_isolation_on_user_listing(client) -> None:
    """Each admin sees only their own tenant's users."""
    token_a = _register(client, "Org One", "a@one-corp.io")["access_token"]
    token_b = _register(client, "Org Two", "b@two-corp.io")["access_token"]

    emails_a = {u["email"] for u in client.get("/api/v1/users", headers=_auth(token_a)).json()}
    emails_b = {u["email"] for u in client.get("/api/v1/users", headers=_auth(token_b)).json()}

    assert emails_a == {"a@one-corp.io"}
    assert emails_b == {"b@two-corp.io"}
    assert "b@two-corp.io" not in emails_a
