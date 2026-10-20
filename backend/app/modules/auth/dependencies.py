from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import PermissionDenied, Unauthenticated
from app.core.security import decode_access_token
from app.infrastructure.db.session import get_db
from app.infrastructure.idempotency import IdempotencyService
from app.infrastructure.redis.client import get_redis
from app.modules.auth.permissions import PermissionService
from app.modules.auth.rate_limit import LoginRateLimiter
from app.modules.auth.repository import (
    AclRepository,
    RefreshTokenRepository,
    TenantRepository,
    UserRepository,
)
from app.modules.auth.service import AuthService
from app.modules.auth.user_service import AdminUserService
from app.shared.actor import ActorContext

bearer = HTTPBearer(auto_error=False)


def get_auth_service(
    db: Annotated[Session, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> AuthService:
    settings = get_settings()
    return AuthService(
        session=db,
        users=UserRepository(db),
        tenants=TenantRepository(db),
        refresh_tokens=RefreshTokenRepository(db),
        rate_limiter=LoginRateLimiter(
            redis,
            settings.login_rate_limit,
            settings.login_rate_window_seconds,
        ),
    )


def get_admin_user_service(
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserService:
    return AdminUserService(
        session=db,
        users=UserRepository(db),
        tenants=TenantRepository(db),
        permissions=PermissionService(AclRepository(db)),
        idempotency=IdempotencyService(db),
    )


def get_current_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> ActorContext:
    if credentials is None:
        raise Unauthenticated()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tid"])
    except Exception as exc:
        raise Unauthenticated() from exc

    users = UserRepository(db)
    tenants = TenantRepository(db)
    user = users.get_by_id(user_id)
    tenant = tenants.get_by_id(tenant_id)
    roles = users.list_roles(user_id, tenant_id)
    if (
        user is None
        or tenant is None
        or not roles
        or not user.is_active
        or tenant.status != "active"
    ):
        raise Unauthenticated()

    return ActorContext(
        user_id=user.id,
        tenant_id=tenant.id,
        email=user.email,
        display_name=user.display_name,
        tenant_slug=tenant.slug,
        tenant_name=tenant.name,
        roles=frozenset(roles),
    )


def require_roles(*allowed: str):
    def dependency(
        actor: Annotated[ActorContext, Depends(get_current_actor)],
    ) -> ActorContext:
        if not actor.roles.intersection(allowed):
            raise PermissionDenied()
        return actor

    return dependency
