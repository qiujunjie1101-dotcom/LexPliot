import os
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://lexpilot:lexpilot@localhost:55432/lexpilot_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:56379/0")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("COOKIE_SECURE", "false")

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

import app.infrastructure.db.registry  # noqa: F401
from alembic import command
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
def clean_tables() -> None:
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))


@pytest.fixture()
def db() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
