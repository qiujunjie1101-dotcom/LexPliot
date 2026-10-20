from typing import cast

from redis import Redis

from app.core.exceptions import RateLimited


class LoginRateLimiter:
    """登录失败限流：按客户端 IP + 邮箱计数。"""

    def __init__(self, redis: Redis, limit: int, window_seconds: int) -> None:
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds

    @staticmethod
    def _key(client_ip: str, email: str) -> str:
        return f"login:fail:{client_ip}:{email.strip().lower()}"

    def check(self, client_ip: str, email: str) -> None:
        key = self._key(client_ip, email)
        value = cast(str | int | None, self.redis.get(key))
        count = int(value) if value is not None else 0
        if count >= self.limit:
            ttl = cast(int, self.redis.ttl(key))
            retry_after = ttl if ttl > 0 else self.window_seconds
            raise RateLimited(max(retry_after, 1))

    def record_failure(self, client_ip: str, email: str) -> None:
        key = self._key(client_ip, email)
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, self.window_seconds)

    def reset(self, client_ip: str, email: str) -> None:
        self.redis.delete(self._key(client_ip, email))
