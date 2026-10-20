from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


# 请求ID中间件
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid4().hex)
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response
