from app.modules.auth.models import RoleBinding, Tenant


def login(
    client,
    *,
    email: str = "admin@example.com",
    password: str = "Admin123!",
    tenant_slug: str | None = "acme",
):
    return client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "tenant_slug": tenant_slug,
        },
    )


def test_login_returns_access_token_and_refresh_cookie(client, tenant_user) -> None:
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["tenant"]["slug"] == "acme"
    assert body["roles"] == ["admin"]
    assert "lexpilot_refresh" in response.cookies


def test_login_rejects_wrong_password(client, tenant_user) -> None:
    response = login(client, password="wrong")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rate_limits_after_five_failures(client, tenant_user) -> None:
    for _ in range(5):
        response = login(client, password="wrong")
        assert response.status_code == 401

    response = login(client, password="wrong")
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert response.headers["retry-after"]


def test_me_requires_access_token(client, tenant_user) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401

    token = login(client).json()["access_token"]
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@example.com"
    assert response.json()["tenant"]["slug"] == "acme"
    assert response.json()["roles"] == ["admin"]


def test_multi_tenant_login_requires_selection(client, tenant_user, db) -> None:
    tenant, user = tenant_user
    second = Tenant(slug="beta", name="Beta")
    db.add(second)
    db.flush()
    db.add(
        RoleBinding(
            tenant_id=second.id,
            user_id=user.id,
            role="legal_reviewer",
        )
    )
    db.commit()

    response = login(client, tenant_slug=None)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TENANT_SELECTION_REQUIRED"
    assert {item["slug"] for item in response.json()["error"]["details"]["tenants"]} == {
        "acme",
        "beta",
    }


def test_refresh_rotates_cookie_and_old_token_reuse_revokes_family(
    client, tenant_user
) -> None:
    login_response = login(client)
    old_cookie = login_response.cookies["lexpilot_refresh"]

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    new_cookie = refresh_response.cookies["lexpilot_refresh"]
    assert new_cookie != old_cookie

    client.cookies.set("lexpilot_refresh", old_cookie, path="/api/v1/auth")
    reused = client.post("/api/v1/auth/refresh")
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "REFRESH_TOKEN_REUSE"


def test_logout_revokes_refresh_token(client, tenant_user) -> None:
    login_response = login(client)
    old_cookie = login_response.cookies["lexpilot_refresh"]

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    client.cookies.set("lexpilot_refresh", old_cookie, path="/api/v1/auth")
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "REFRESH_TOKEN_INVALID"


def test_switch_tenant_returns_new_tenant_context(client, tenant_user, db) -> None:
    tenant, user = tenant_user
    second = Tenant(slug="beta", name="Beta")
    db.add(second)
    db.flush()
    db.add(
        RoleBinding(
            tenant_id=second.id,
            user_id=user.id,
            role="legal_reviewer",
        )
    )
    db.commit()

    login_response = login(client)
    assert login_response.status_code == 200

    response = client.post(
        "/api/v1/auth/switch-tenant",
        json={"tenant_slug": "beta"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tenant"]["slug"] == "beta"
    assert body["roles"] == ["legal_reviewer"]
