from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.infrastructure.idempotency import IdempotencyKey
from app.modules.auth.models import ResourceAcl, RoleBinding, Tenant, User

EXPECTED_TABLES = {
    "tenants",
    "users",
    "role_bindings",
    "refresh_tokens",
    "resource_acl",
    "idempotency_keys",
}


def test_expected_tables_exist(db) -> None:
    assert EXPECTED_TABLES <= set(inspect(db.get_bind()).get_table_names())


def test_duplicate_tenant_slug_is_rejected(db) -> None:
    db.add(Tenant(slug="acme", name="Acme"))
    db.commit()
    db.add(Tenant(slug="acme", name="Other"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_duplicate_role_binding_is_rejected(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    user = User(email="a@example.com", password_hash="x", display_name="A")
    db.add_all([tenant, user])
    db.flush()
    db.add(RoleBinding(tenant_id=tenant.id, user_id=user.id, role="admin"))
    db.commit()
    db.add(RoleBinding(tenant_id=tenant.id, user_id=user.id, role="admin"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_resource_acl_subject_must_be_exclusive(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    db.add(tenant)
    db.flush()
    db.add(
        ResourceAcl(
            tenant_id=tenant.id,
            resource_type="contract",
            resource_id=tenant.id,
            subject_type="user",
            user_id=None,
            role="admin",
            permission="read",
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_idempotency_composite_key_is_unique(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    db.add(tenant)
    db.flush()
    row = IdempotencyKey(
        tenant_id=tenant.id,
        key="create-user-1",
        request_hash="a" * 64,
        response_status=201,
        response_body={"id": "1"},
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(row)
    db.commit()
    db.expunge_all()
    db.add(
        IdempotencyKey(
            tenant_id=tenant.id,
            key="create-user-1",
            request_hash="b" * 64,
            response_status=201,
            response_body={"id": "2"},
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
