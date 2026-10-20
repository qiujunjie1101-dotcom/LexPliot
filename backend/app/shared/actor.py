from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ActorContext:
    """当前请求的操作者上下文，供 Service 做权限与租户校验。"""

    user_id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    tenant_slug: str
    tenant_name: str
    roles: frozenset[str]
