from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.auth.models import RefreshToken, RoleBinding, Tenant, User


class TenantRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        return self.session.get(Tenant, tenant_id)

    def get_by_slug(self, slug: str) -> Tenant | None:
        return self.session.scalar(select(Tenant).where(Tenant.slug == slug))


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
