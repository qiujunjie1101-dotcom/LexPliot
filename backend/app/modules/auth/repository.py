from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.modules.auth.models import (
    RefreshToken,
    ResourceAcl,
    RoleBinding,
    Tenant,
    User,
)


class TenantRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        return self.session.get(Tenant, tenant_id)

    def get_by_slug(self, slug: str) -> Tenant | None:
        return self.session.scalar(select(Tenant).where(Tenant.slug == slug))

    def create(self, *, slug: str, name: str) -> Tenant:
        tenant = Tenant(slug=slug, name=name)
        self.session.add(tenant)
        self.session.flush()
        return tenant


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(User.email == email.strip().lower()))

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.session.get(User, user_id)

    def list_memberships(self, user_id: UUID) -> list[tuple[RoleBinding, Tenant]]:
        rows = self.session.execute(
            select(RoleBinding, Tenant)
            .join(Tenant, Tenant.id == RoleBinding.tenant_id)
            .where(RoleBinding.user_id == user_id, Tenant.status == "active")
            .order_by(Tenant.slug)
        ).all()
        return [(binding, tenant) for binding, tenant in rows]

    def list_roles(self, user_id: UUID, tenant_id: UUID) -> list[str]:
        return list(
            self.session.scalars(
                select(RoleBinding.role).where(
                    RoleBinding.user_id == user_id,
                    RoleBinding.tenant_id == tenant_id,
                )
            ).all()
        )

    def create_user(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            display_name=display_name,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def get_role_binding(
        self, tenant_id: UUID, user_id: UUID, role: str
    ) -> RoleBinding | None:
        return self.session.scalar(
            select(RoleBinding).where(
                RoleBinding.tenant_id == tenant_id,
                RoleBinding.user_id == user_id,
                RoleBinding.role == role,
            )
        )

    def add_role_binding(
        self, tenant_id: UUID, user_id: UUID, role: str
    ) -> RoleBinding:
        binding = RoleBinding(
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
        )
        self.session.add(binding)
        self.session.flush()
        return binding

    def list_tenant_users(self, tenant_id: UUID) -> list[User]:
        return list(
            self.session.scalars(
                select(User)
                .join(RoleBinding, RoleBinding.user_id == User.id)
                .where(RoleBinding.tenant_id == tenant_id)
                .order_by(User.email)
                .distinct()
            ).all()
        )


class AclRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_actor_resource(
        self,
        *,
        tenant_id: UUID,
        resource_type: str,
        resource_id: UUID,
        user_id: UUID,
        roles: frozenset[str],
    ) -> list[ResourceAcl]:
        return list(
            self.session.scalars(
                select(ResourceAcl).where(
                    ResourceAcl.tenant_id == tenant_id,
                    ResourceAcl.resource_type == resource_type,
                    ResourceAcl.resource_id == resource_id,
                    or_(
                        (ResourceAcl.subject_type == "user")
                        & (ResourceAcl.user_id == user_id),
                        (ResourceAcl.subject_type == "role")
                        & (ResourceAcl.role.in_(list(roles))),
                    ),
                )
            ).all()
        )

    def add(
        self,
        *,
        tenant_id: UUID,
        resource_type: str,
        resource_id: UUID,
        subject_type: str,
        user_id: UUID | None,
        role: str | None,
        permission: str,
    ) -> ResourceAcl:
        entry = ResourceAcl(
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            subject_type=subject_type,
            user_id=user_id,
            role=role,
            permission=permission,
        )
        self.session.add(entry)
        self.session.flush()
        return entry


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        user_id: UUID,
        tenant_id: UUID,
        token_hash: str,
        family_id: UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            tenant_id=tenant_id,
            token_hash=token_hash,
            family_id=family_id,
            expires_at=expires_at,
        )
        self.session.add(token)
        self.session.flush()
        return token

    def find_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )

    def find_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        return self.session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .with_for_update()
        ).scalar_one_or_none()

    def revoke(self, token: RefreshToken, revoked_at: datetime) -> None:
        token.revoked_at = revoked_at
        self.session.flush()

    def revoke_family(self, family_id: UUID, revoked_at: datetime) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.family_id == family_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )
