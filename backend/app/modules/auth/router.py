from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response

from app.core.config import get_settings
from app.core.exceptions import Unauthenticated
from app.modules.auth.dependencies import get_auth_service, get_current_actor
from app.modules.auth.schemas import (
    LoginRequest,
    MeResponse,
    SwitchTenantRequest,
    TenantInfo,
    TokenResponse,
    UserInfo,
)
from app.modules.auth.service import AuthResult, AuthService
from app.shared.actor import ActorContext

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = get_settings().refresh_cookie_name
COOKIE_PATH = "/api/v1/auth"


def _set_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=COOKIE_PATH,
        max_age=settings.refresh_token_days * 86400,
    )


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(
        key=get_settings().refresh_cookie_name,
        path=COOKIE_PATH,
    )


def _token_response(result: AuthResult) -> TokenResponse:
    settings = get_settings()
    return TokenResponse(
        access_token=result.access_token,
        expires_in=settings.access_token_minutes * 60,
        user=UserInfo(
            id=result.user.id,
            email=result.user.email,
            display_name=result.user.display_name,
        ),
        tenant=TenantInfo(
            id=result.tenant.id,
            slug=result.tenant.slug,
            name=result.tenant.name,
        ),
        roles=result.roles,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"
    result = service.authenticate(
        email=str(payload.email),
        password=payload.password,
        tenant_slug=payload.tenant_slug,
        client_ip=client_ip,
    )
    _set_cookie(response, result.refresh_token)
    return _token_response(result)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[
        str | None, Cookie(alias=REFRESH_COOKIE_NAME)
    ] = None,
) -> TokenResponse:
    if not refresh_token:
        raise Unauthenticated("缺少 Refresh Token")
    result = service.refresh(refresh_token)
    _set_cookie(response, result.refresh_token)
    return _token_response(result)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[
        str | None, Cookie(alias=REFRESH_COOKIE_NAME)
    ] = None,
) -> Response:
    if refresh_token:
        service.revoke_refresh_token(refresh_token)
    _clear_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=MeResponse)
def me(
    actor: Annotated[ActorContext, Depends(get_current_actor)],
) -> MeResponse:
    return MeResponse(
        user=UserInfo(
            id=actor.user_id,
            email=actor.email,
            display_name=actor.display_name,
        ),
        tenant=TenantInfo(
            id=actor.tenant_id,
            slug=actor.tenant_slug,
            name=actor.tenant_name,
        ),
        roles=sorted(actor.roles),
    )


@router.post("/switch-tenant", response_model=TokenResponse)
def switch_tenant(
    payload: SwitchTenantRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[
        str | None, Cookie(alias=REFRESH_COOKIE_NAME)
    ] = None,
) -> TokenResponse:
    if not refresh_token:
        raise Unauthenticated("缺少 Refresh Token")
    result = service.switch_tenant(refresh_token, payload.tenant_slug)
    _set_cookie(response, result.refresh_token)
    return _token_response(result)
