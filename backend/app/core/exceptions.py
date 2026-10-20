from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """应用领域异常基类，HTTP 状态码由接口层统一映射。"""

    code = "APP_ERROR"
    status_code = 400

    def __init__(self, message: str | None = None, **details: Any) -> None:
        self.message = message or "Application error"
        self.details = details
        super().__init__(self.message)


class InvalidCredentials(AppError):
    code = "INVALID_CREDENTIALS"
    status_code = 401

    def __init__(self) -> None:
        super().__init__("邮箱或密码错误")


class TenantSelectionRequired(AppError):
    code = "TENANT_SELECTION_REQUIRED"
    status_code = 400

    def __init__(self, tenants: list[dict[str, str]]) -> None:
        super().__init__("需要选择登录租户", tenants=tenants)


class MembershipNotFound(AppError):
    code = "MEMBERSHIP_NOT_FOUND"
    status_code = 403

    def __init__(self) -> None:
        super().__init__("用户不属于该租户")


class RefreshTokenInvalid(AppError):
    code = "REFRESH_TOKEN_INVALID"
    status_code = 401

    def __init__(self) -> None:
        super().__init__("Refresh Token 无效或已过期")


class RefreshTokenReuse(AppError):
    code = "REFRESH_TOKEN_REUSE"
    status_code = 401

    def __init__(self) -> None:
        super().__init__("检测到 Refresh Token 重放，已撤销整个令牌家族")


class Unauthenticated(AppError):
    code = "UNAUTHENTICATED"
    status_code = 401

    def __init__(self, message: str = "未登录或登录已过期") -> None:
        super().__init__(message)


class PermissionDenied(AppError):
    code = "PERMISSION_DENIED"
    status_code = 403

    def __init__(self, message: str = "权限不足") -> None:
        super().__init__(message)


class RateLimited(AppError):
    code = "RATE_LIMITED"
    status_code = 429

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(
            "登录失败次数过多，请稍后再试",
            retry_after=retry_after,
        )


def install_exception_handlers(app: FastAPI) -> None:
    """把领域异常与参数校验异常统一转换为项目错误格式。"""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers: dict[str, str] = {}
        if isinstance(exc, RateLimited):
            headers["Retry-After"] = str(exc.retry_after)
        content = {
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": getattr(request.state, "request_id", None),
                "details": exc.details,
            }
        }
        return JSONResponse(
            status_code=exc.status_code,
            content=jsonable_encoder(content),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        content = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数校验失败",
                "request_id": getattr(request.state, "request_id", None),
                "details": exc.errors(),
            }
        }
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(content),
        )
