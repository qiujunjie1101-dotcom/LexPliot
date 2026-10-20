from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import install_exception_handlers
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.modules.auth.admin_router import router as admin_router
from app.modules.auth.router import router as auth_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="LexPilot", version="0.1.0", lifespan=lifespan)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_exception_handlers(app)
    app.include_router(health_router, tags=["health"])
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    return app


app = create_app()
