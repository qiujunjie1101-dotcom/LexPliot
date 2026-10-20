from uuid import uuid4

import pytest

from app.core.exceptions import PermissionDenied
from app.modules.auth.models import Tenant
from app.modules.auth.permissions import PermissionService, ResourceRef
from app.modules.auth.repository import AclRepository
from app.shared.actor import ActorContext


def make_actor(tenant_id, role: str) -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        tenant_id=tenant_id,
        email="user@example.com",
        display_name="User",
        tenant_slug="acme",
        tenant_name="Acme",
        roles=frozenset({role}),
    )


def test_admin_can_manage_users(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    db.add(tenant)
    db.commit()
    service = PermissionService(AclRepository(db))
    service.authorize(make_actor(tenant.id, "admin"), "user:manage")


def test_submitter_cannot_manage_users(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    db.add(tenant)
    db.commit()
    service = PermissionService(AclRepository(db))
    with pytest.raises(PermissionDenied):
        service.authorize(make_actor(tenant.id, "business_submitter"), "user:manage")


def test_legal_reviewer_can_read_contract(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    db.add(tenant)
    db.commit()
    resource = ResourceRef(
        tenant_id=tenant.id,
        resource_type="contract",
        resource_id=uuid4(),
    )
    service = PermissionService(AclRepository(db))
    service.authorize(make_actor(tenant.id, "legal_reviewer"), "contract:read", resource)


def test_acl_deny_overrides_role_permission(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    db.add(tenant)
    db.flush()
    resource = ResourceRef(
        tenant_id=tenant.id,
        resource_type="contract",
        resource_id=uuid4(),
    )
    acl = AclRepository(db)
    acl.add(
        tenant_id=tenant.id,
        resource_type=resource.resource_type,
        resource_id=resource.resource_id,
        subject_type="role",
        user_id=None,
        role="legal_reviewer",
        permission="deny",
    )
    db.commit()

    service = PermissionService(AclRepository(db))
    with pytest.raises(PermissionDenied):
        service.authorize(
            make_actor(tenant.id, "legal_reviewer"),
            "contract:read",
            resource,
        )


def test_acl_can_grant_permission_outside_role(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    db.add(tenant)
    db.flush()
    resource = ResourceRef(
        tenant_id=tenant.id,
        resource_type="contract",
        resource_id=uuid4(),
    )
    acl = AclRepository(db)
    acl.add(
        tenant_id=tenant.id,
        resource_type=resource.resource_type,
        resource_id=resource.resource_id,
        subject_type="role",
        user_id=None,
        role="business_submitter",
        permission="contract:write",
    )
    db.commit()

    service = PermissionService(AclRepository(db))
    service.authorize(
        make_actor(tenant.id, "business_submitter"),
        "contract:write",
        resource,
    )


def test_cross_tenant_resource_is_denied(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    other = Tenant(slug="beta", name="Beta")
    db.add_all([tenant, other])
    db.commit()
    resource = ResourceRef(
        tenant_id=other.id,
        resource_type="contract",
        resource_id=uuid4(),
    )
    service = PermissionService(AclRepository(db))
    with pytest.raises(PermissionDenied):
        service.authorize(
            make_actor(tenant.id, "legal_reviewer"),
            "contract:read",
            resource,
        )
