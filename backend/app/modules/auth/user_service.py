from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import TenantNotFound, UserAlreadyExists
from app.core.security import hash_password
from app.infrastructure.idempotency import (
    IdempotencyService,
    request_hash,
)
from app.modules.auth.models import User
from app.modules.auth.permissions import PermissionService
from app.modules.auth.repository import TenantRepository, UserRepository
from app.modules.auth.schemas import AdminUserCreate, AdminUserRead
from app.shared.actor import ActorContext


@dataclass(frozen=True)
class CreateUserResult:
    status_code: int
    body: dict[str, Any]
    replayed: bool


class AdminUserService:
    """管理员用户管理；Service 负责权限检查与事务边界。"""

    def __init__(
        self,
        *,
        session: Session,
        users: UserRepository,
        tenants: TenantRepository,
        permissions: PermissionService,
        idempotency: IdempotencyService,
    ) -> None:
        self.session = session
        self.users = users
        self.tenants = tenants
        self.permissions = permissions
        self.idempotency = idempotency

    def list_users(self, actor: ActorContext) -> list[AdminUserRead]:
        self.permissions.authorize(actor, "user:manage")
        users = self.users.list_tenant_users(actor.tenant_id)
        return [self._to_read(actor.tenant_id, user) for user in users]

    def create_user(
        self,
        actor: ActorContext,
        payload: AdminUserCreate,
        idempotency_key: str | None,
    ) -> CreateUserResult:
        self.permissions.authorize(actor, "user:manage")

        payload_dict = payload.model_dump(mode="json")
        payload_hash = request_hash(payload_dict)
        if idempotency_key:
            existing = self.idempotency.get(
                actor.tenant_id,
                idempotency_key,
                payload_hash,
            )
            if existing is not None:
                return CreateUserResult(
                    status_code=existing.response_status,
                    body=existing.response_body,
                    replayed=True,
                )

        email = str(payload.email).strip().lower()
        user = self.users.get_by_email(email)
        if user is None:
            user = self.users.create_user(
                email=email,
                password_hash=hash_password(payload.password),
                display_name=payload.display_name,
            )

        existing_binding = self.users.get_role_binding(
            actor.tenant_id,
            user.id,
            payload.role,
        )
        if existing_binding is not None:
            self.session.rollback()
            raise UserAlreadyExists()

        self.users.add_role_binding(actor.tenant_id, user.id, payload.role)
        self.session.flush()
        result = self._to_read(actor.tenant_id, user).model_dump(mode="json")

        if idempotency_key:
            self.idempotency.save(
                actor.tenant_id,
                idempotency_key,
                payload_hash,
                201,
                result,
            )

        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return CreateUserResult(status_code=201, body=result, replayed=False)

    def bootstrap_admin(
        self,
        *,
        tenant_slug: str,
        email: str,
        password: str,
        display_name: str,
    ) -> User:
        """CLI 使用：不依赖登录用户，仍复用用户与角色创建逻辑。"""
        tenant = self.tenants.get_by_slug(tenant_slug)
        if tenant is None:
            raise TenantNotFound()

        normalized_email = email.strip().lower()
        user = self.users.get_by_email(normalized_email)
        if user is None:
            user = self.users.create_user(
                email=normalized_email,
                password_hash=hash_password(password),
                display_name=display_name,
            )

        binding = self.users.get_role_binding(tenant.id, user.id, "admin")
        if binding is None:
            self.users.add_role_binding(tenant.id, user.id, "admin")

        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return user

    def _to_read(self, tenant_id: UUID, user: User) -> AdminUserRead:
        roles = sorted(self.users.list_roles(user.id, tenant_id))
        return AdminUserRead(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            roles=roles,
        )
