from app.core.security import hash_password
from app.modules.auth.models import RoleBinding, Tenant, User


def login(client, email: str = "admin@example.com", password: str = "Admin123!"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "tenant_slug": "acme"},
    )


def admin_headers(client) -> dict[str, str]:
    token = login(client).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_create_and_list_users(client, tenant_user) -> None:
    headers = admin_headers(client)
    created = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "email": "reviewer@example.com",
            "password": "Reviewer123!",
            "display_name": "Reviewer",
            "role": "legal_reviewer",
        },
    )
    assert created.status_code == 201
    assert created.json()["roles"] == ["legal_reviewer"]

    listed = client.get("/api/v1/admin/users", headers=headers)
    assert listed.status_code == 200
    assert {item["email"] for item in listed.json()} == {
        "admin@example.com",
        "reviewer@example.com",
    }


def test_non_admin_cannot_list_users(client, tenant_user) -> None:
    headers = admin_headers(client)
    client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "email": "submitter@example.com",
            "password": "Submitter123!",
            "display_name": "Submitter",
            "role": "business_submitter",
        },
    )

    submitter_login = login(
        client,
        email="submitter@example.com",
        password="Submitter123!",
    )
    token = submitter_login.json()["access_token"]
    response = client.get(
        "/api/v1/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_user_creation_is_idempotent(client, tenant_user) -> None:
    headers = {
        **admin_headers(client),
        "Idempotency-Key": "create-reviewer-1",
    }
    payload = {
        "email": "reviewer2@example.com",
        "password": "Reviewer123!",
        "display_name": "Reviewer",
        "role": "legal_reviewer",
    }
    first = client.post("/api/v1/admin/users", headers=headers, json=payload)
    second = client.post("/api/v1/admin/users", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    conflict = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={**payload, "display_name": "Other"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"


def test_duplicate_role_is_rejected(client, tenant_user) -> None:
    headers = admin_headers(client)
    payload = {
        "email": "reviewer3@example.com",
        "password": "Reviewer123!",
        "display_name": "Reviewer",
        "role": "legal_reviewer",
    }
    first = client.post("/api/v1/admin/users", headers=headers, json=payload)
    assert first.status_code == 201
    second = client.post("/api/v1/admin/users", headers=headers, json=payload)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "USER_ALREADY_EXISTS"


def test_cross_tenant_users_are_isolated(client, tenant_user, db) -> None:
    other = Tenant(slug="beta", name="Beta")
    beta_user = User(
        email="beta@example.com",
        password_hash=hash_password("Beta123!"),
        display_name="Beta User",
    )
    db.add_all([other, beta_user])
    db.flush()
    db.add(
        RoleBinding(
            tenant_id=other.id,
            user_id=beta_user.id,
            role="legal_reviewer",
        )
    )
    db.commit()

    response = client.get(
        "/api/v1/admin/users",
        headers=admin_headers(client),
    )
    assert response.status_code == 200
    assert "beta@example.com" not in {item["email"] for item in response.json()}
