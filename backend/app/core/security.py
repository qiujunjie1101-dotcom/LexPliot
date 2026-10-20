import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """使用 Argon2 生成密码哈希。"""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与 Argon2 哈希是否匹配。"""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, ValueError):
        return False


def create_access_token(*, user_id: UUID, tenant_id: UUID, roles: list[str]) -> str:
    """签发 Access Token，Header 中携带 kid 以支持密钥轮换。"""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "roles": roles,
        "type": "access",
        "jti": uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_keyring[settings.jwt_active_kid],
        algorithm=settings.jwt_algorithm,
        headers={"kid": settings.jwt_active_kid},
    )


def decode_access_token(token: str, *, forced_kid: str | None = None) -> dict[str, Any]:
    """校验 Access Token 并返回 payload。"""
    settings = get_settings()
    header = jwt.get_unverified_header(token)
    kid = forced_kid or header.get("kid")
    key = settings.jwt_keyring.get(kid) if kid else None
    if key is None:
        raise jwt.InvalidTokenError("unknown jwt kid")
    payload = jwt.decode(token, key, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload


def generate_refresh_token() -> str:
    """生成不可预测的 Refresh Token 明文。"""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """数据库只保存 Refresh Token 的 SHA-256 哈希。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
