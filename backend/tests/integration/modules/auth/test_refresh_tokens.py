from datetime import UTC, datetime, timedelta

import pytest
from uuid6 import uuid7

from app.core.exceptions import (
    InvalidCredentials,
    RefreshTokenInvalid,
    RefreshTokenReuse,
    TenantSelectionRequired,
)
from app.core.security import (
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.modules.auth.models import RefreshToken, RoleBinding, Tenant
from app.modules.auth.repository import (
    RefreshTokenRepository,
    TenantRepository,
    UserRepository,
)
from app.modules.auth.service import AuthService


def make_service(db) -> AuthService:
    return AuthService(
        session=db,
        users=UserRepository(db),
        tenants=TenantRepository(db),
        refresh_tokens=RefreshTokenRepository(db),
    )


def test_authenticate_issues_access_and_refresh_token(db, tenant_user) -> None:
    service = make_service(db)
    result = service.authenticate(
        email="admin@example.com",
        password="Admin123!",
        tenant_slug="acme",
    )
    assert result.tenant.slug == "acme"
    assert result.roles == ["admin"]
    assert result.refresh_token

    payload = decode_access_token(result.access_token)
    assert payload["sub"] == str(result.user.id)
    assert payload["tid"] == str(result.tenant.id)
    assert payload["roles"] == ["admin"]


def test_authenticate_rejects_wrong_password(db, tenant_user) -> None:
    service = make_service(db)
    with pytest.raises(InvalidCredentials):
        service.authenticate(
            email="admin@example.com",
            password="wrong",
            tenant_slug="acme",
        )


def test_authenticate_requires_tenant_selection(db, tenant_user) -> None:
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

    service = make_service(db)
    with pytest.raises(TenantSelectionRequired) as exc_info:
        service.authenticate(
            email="admin@example.com",
            password="Admin123!",
            tenant_slug=None,
        )
    assert {item["slug"] for item in exc_info.value.details["tenants"]} == {
        "acme",
        "beta",
    }


def test_refresh_rotation_and_reuse_detection(db, tenant_user) -> None:
    service = make_service(db)
    result = service.authenticate(
        email="admin@example.com",
        password="Admin123!",
        tenant_slug="acme",
    )
    old_token = result.refresh_token

    new_token, user, tenant = service.rotate_refresh_token(old_token)
    assert new_token != old_token
    assert user.id == result.user.id
    assert tenant.id == result.tenant.id

    with pytest.raises(RefreshTokenReuse):
        service.rotate_refresh_token(old_token)

    tokens = db.query(RefreshToken).all()
    assert len(tokens) == 2
    assert all(token.revoked_at is not None for token in tokens)


def test_expired_refresh_token_is_rejected(db, tenant_user) -> None:
    tenant, user = tenant_user
    raw_token = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            tenant_id=tenant.id,
            token_hash=hash_refresh_token(raw_token),
            family_id=uuid7(),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    db.commit()

    service = make_service(db)
    with pytest.raises(RefreshTokenInvalid):
        service.rotate_refresh_token(raw_token)


def test_revoked_refresh_token_cannot_be_rotated(db, tenant_user) -> None:
    service = make_service(db)
    result = service.authenticate(
        email="admin@example.com",
        password="Admin123!",
        tenant_slug="acme",
    )
    service.revoke_refresh_token(result.refresh_token)
    with pytest.raises(RefreshTokenInvalid):
        service.rotate_refresh_token(result.refresh_token)
