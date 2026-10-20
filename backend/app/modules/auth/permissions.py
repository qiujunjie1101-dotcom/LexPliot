from dataclasses import dataclass
from uuid import UUID

from app.core.exceptions import PermissionDenied
from app.modules.auth.repository import AclRepository
from app.shared.actor import ActorContext

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "legal_reviewer": {
        "user:read",
        "contract:read",
        "review:read",
        "review:write",
        "human_review:submit",
        "knowledge:read",
    },
    "business_submitter": {
        "contract:create",
        "contract:read",
        "review:read",
    },
}


@dataclass(frozen=True)
class ResourceRef:
    tenant_id: UUID
    resource_type: str
    resource_id: UUID


class PermissionService:
    """RBAC + 资源 ACL。"""

    def __init__(self, acl: AclRepository) -> None:
        self.acl = acl

    def authorize(
        self,
        actor: ActorContext,
        permission: str,
        resource: ResourceRef | None = None,
    ) -> None:
        if resource is not None and resource.tenant_id != actor.tenant_id:
            raise PermissionDenied("不能访问其他租户的资源")

        if "admin" in actor.roles:
            return

        if resource is not None:
            entries = self.acl.list_for_actor_resource(
                tenant_id=actor.tenant_id,
                resource_type=resource.resource_type,
                resource_id=resource.resource_id,
                user_id=actor.user_id,
                roles=actor.roles,
            )
            if entries:
                if any(entry.permission == "deny" for entry in entries):
                    raise PermissionDenied()
                if any(
                    entry.permission in {permission, "admin"}
                    for entry in entries
                ):
                    return
                raise PermissionDenied()

        for role in actor.roles:
            permissions = ROLE_PERMISSIONS.get(role, set())
            if permission in permissions or "*" in permissions:
                return
        raise PermissionDenied()
