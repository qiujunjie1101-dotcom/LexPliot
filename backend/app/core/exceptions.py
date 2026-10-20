from typing import Any


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
