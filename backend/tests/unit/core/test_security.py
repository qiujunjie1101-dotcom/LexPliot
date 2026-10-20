from uuid import uuid4

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    hashed = hash_password("Secret123!")
    assert hashed != "Secret123!"
    assert verify_password("Secret123!", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_access_token_round_trip() -> None:
    user_id = uuid4()
    tenant_id = uuid4()
    token = create_access_token(user_id=user_id, tenant_id=tenant_id, roles=["admin"])
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["tid"] == str(tenant_id)
    assert payload["roles"] == ["admin"]
    assert payload["type"] == "access"


def test_access_token_with_unknown_kid_is_rejected() -> None:
    token = create_access_token(user_id=uuid4(), tenant_id=uuid4(), roles=["admin"])
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, forced_kid="missing")


def test_refresh_token_generation_and_hashing() -> None:
    first = generate_refresh_token()
    second = generate_refresh_token()
    assert first != second
    assert hash_refresh_token(first) == hash_refresh_token(first)
    assert hash_refresh_token(first) != hash_refresh_token(second)
    assert len(hash_refresh_token(first)) == 64
