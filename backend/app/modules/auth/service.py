from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.config import get_settings
from app.core.exceptions import (
    InvalidCredentials,
    MembershipNotFound,
    RefreshTokenInvalid,
    RefreshTokenReuse,
    TenantSelectionRequired,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.modules.auth.models import Tenant, User
from app.modules.auth.rate_limit import LoginRateLimiter
from app.modules.auth.repository import (
    RefreshTokenRepository,
    TenantRepository,
    UserRepository,
)


@dataclass(frozen=True)
class AuthResult:
    access_token: str
    refresh_token: str
    user: User
    tenant: Tenant
    roles: list[str]


class AuthService:
    """认证业务服务；事务提交与回滚由 Service 负责。"""

    def __init__(
        self,
        *,
        session: Session,
        users: UserRepository,
        tenants: TenantRepository,
        refresh_tokens: RefreshTokenRepository,
        rate_limiter: LoginRateLimiter | None = None,
    ) -> None:
        self.session = session
        self.users = users
        self.tenants = tenants
        self.refresh_tokens = refresh_tokens
        self.rate_limiter = rate_limiter

    def authenticate(
        self,
        *,
        email: str,
        password: str,
        tenant_slug: str | None = None,
        client_ip: str | None = None,
    ) -> AuthResult:
        if self.rate_limiter is not None and client_ip is not None:
            self.rate_limiter.check(client_ip, email)

        try:
            user = self.users.get_by_email(email)
            if user is None or not user.is_active:
                raise InvalidCredentials()
            if not verify_password(password, user.password_hash):
                raise InvalidCredentials()

            memberships = self.users.list_memberships(user.id)
            if not memberships:
                raise MembershipNotFound()

            if tenant_slug:
                matching = [
                    (binding, tenant)
                    for binding, tenant in memberships
                    if tenant.slug == tenant_slug
                ]
                if not matching:
                    raise MembershipNotFound()
            elif len(memberships) > 1:
                raise TenantSelectionRequired(
                    [
                        {"slug": tenant.slug, "name": tenant.name}
                        for _, tenant in memberships
                    ]
                )
            else:
                matching = memberships
        except (InvalidCredentials, MembershipNotFound):
            if self.rate_limiter is not None and client_ip is not None:
                self.rate_limiter.record_failure(client_ip, email)
            raise

        _, tenant = matching[0]
        roles = self.users.list_roles(user.id, tenant.id)

        try:
            refresh_token = self._create_refresh_token(user.id, tenant.id)
            access_token = create_access_token(
                user_id=user.id,
                tenant_id=tenant.id,
                roles=roles,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        if self.rate_limiter is not None and client_ip is not None:
            self.rate_limiter.reset(client_ip, email)

        return AuthResult(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user,
            tenant=tenant,
            roles=roles,
        )

    def rotate_refresh_token(self, raw_token: str) -> tuple[str, User, Tenant]:
        now = datetime.now(UTC)
        token = self.refresh_tokens.find_by_hash_for_update(
            hash_refresh_token(raw_token)
        )
        if token is None or token.expires_at <= now:
            self.session.rollback()
            raise RefreshTokenInvalid()
        if token.revoked_at is not None:
            if token.replaced_by_id is not None:
                # 已轮换的旧 Token 被重复使用：撤销整条家族链
                self.refresh_tokens.revoke_family(token.family_id, now)
                self.session.commit()
                raise RefreshTokenReuse()
            # 主动登出撤销的 Token：视为无效，不再触发家族撤销
            self.session.rollback()
            raise RefreshTokenInvalid()

        user = self.users.get_by_id(token.user_id)
        tenant = self.tenants.get_by_id(token.tenant_id)
        if (
            user is None
            or tenant is None
            or not user.is_active
            or tenant.status != "active"
        ):
            self.session.rollback()
            raise RefreshTokenInvalid()

        new_raw_token = generate_refresh_token()
        try:
            new_token = self.refresh_tokens.create(
                user_id=token.user_id,
                tenant_id=token.tenant_id,
                token_hash=hash_refresh_token(new_raw_token),
                family_id=token.family_id,
                expires_at=now + timedelta(days=get_settings().refresh_token_days),
            )
            self.refresh_tokens.revoke(token, now)
            token.replaced_by_id = new_token.id
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return new_raw_token, user, tenant

    def revoke_refresh_token(self, raw_token: str) -> None:
        token = self.refresh_tokens.find_by_hash(hash_refresh_token(raw_token))
        if token is None or token.revoked_at is not None:
            return
        self.refresh_tokens.revoke(token, datetime.now(UTC))
        self.session.commit()

    def refresh(self, raw_token: str) -> AuthResult:
        new_raw_token, user, tenant = self.rotate_refresh_token(raw_token)
        roles = self.users.list_roles(user.id, tenant.id)
        access_token = create_access_token(
            user_id=user.id,
            tenant_id=tenant.id,
            roles=roles,
        )
        return AuthResult(
            access_token=access_token,
            refresh_token=new_raw_token,
            user=user,
            tenant=tenant,
            roles=roles,
        )

    def switch_tenant(self, raw_token: str, tenant_slug: str) -> AuthResult:
        now = datetime.now(UTC)
        token = self.refresh_tokens.find_by_hash_for_update(
            hash_refresh_token(raw_token)
        )
        if token is None or token.expires_at <= now or token.revoked_at is not None:
            self.session.rollback()
            raise RefreshTokenInvalid()

        user = self.users.get_by_id(token.user_id)
        if user is None or not user.is_active:
            self.session.rollback()
            raise RefreshTokenInvalid()

        memberships = self.users.list_memberships(user.id)
        matching = [
            (binding, tenant)
            for binding, tenant in memberships
            if tenant.slug == tenant_slug
        ]
        if not matching:
            self.session.rollback()
            raise MembershipNotFound()

        _, tenant = matching[0]
        roles = self.users.list_roles(user.id, tenant.id)
        new_raw_token = generate_refresh_token()
        try:
            self.refresh_tokens.revoke(token, now)
            self.refresh_tokens.create(
                user_id=user.id,
                tenant_id=tenant.id,
                token_hash=hash_refresh_token(new_raw_token),
                family_id=uuid7(),
                expires_at=now + timedelta(days=get_settings().refresh_token_days),
            )
            access_token = create_access_token(
                user_id=user.id,
                tenant_id=tenant.id,
                roles=roles,
            )
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return AuthResult(
            access_token=access_token,
            refresh_token=new_raw_token,
            user=user,
            tenant=tenant,
            roles=roles,
        )

    def _create_refresh_token(self, user_id: UUID, tenant_id: UUID) -> str:
        raw_token = generate_refresh_token()
        self.refresh_tokens.create(
            user_id=user_id,
            tenant_id=tenant_id,
            token_hash=hash_refresh_token(raw_token),
            family_id=uuid7(),
            expires_at=datetime.now(UTC)
            + timedelta(days=get_settings().refresh_token_days),
        )
        return raw_token
