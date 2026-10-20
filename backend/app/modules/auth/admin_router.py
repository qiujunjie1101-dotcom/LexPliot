from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.modules.auth.dependencies import (
    get_admin_user_service,
    require_roles,
)
from app.modules.auth.schemas import AdminUserCreate, AdminUserRead
from app.modules.auth.user_service import AdminUserService
from app.shared.actor import ActorContext

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=list[AdminUserRead])
def list_users(
    actor: Annotated[ActorContext, Depends(require_roles("admin"))],
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
) -> list[AdminUserRead]:
    return service.list_users(actor)


@router.post("", response_model=AdminUserRead, status_code=201)
def create_user(
    payload: AdminUserCreate,
    actor: Annotated[ActorContext, Depends(require_roles("admin"))],
    service: Annotated[AdminUserService, Depends(get_admin_user_service)],
    idempotency_key: Annotated[
        str | None, Header(alias="Idempotency-Key")
    ] = None,
) -> JSONResponse:
    result = service.create_user(actor, payload, idempotency_key)
    return JSONResponse(status_code=result.status_code, content=result.body)
