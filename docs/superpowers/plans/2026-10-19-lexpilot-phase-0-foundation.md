# LexPilot Phase 0 — Foundation & Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the Phase 0 vertical slice: runnable FastAPI + PostgreSQL + Redis stack, JWT authentication with refresh rotation, multi-tenant RBAC/ACL, admin user management with idempotency, a Vue 3 login/dashboard, and CI.

**Architecture:** Modular monolith. Synchronous SQLAlchemy 2.0 sessions and FastAPI route handlers; PostgreSQL 16 + pgvector for business data; Redis for login rate limiting; Vue 3 SPA with Tailwind + shadcn-vue-style local components. No Celery, contract upload, parsing, knowledge base, or review workflow in this phase.

**Tech Stack:** Python 3.12 (via uv), FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL 16 + pgvector, Redis 7, PyJWT, Argon2, Vue 3, Vite, Tailwind CSS v4, Pinia, Vitest, Playwright, GitHub Actions.

## Global Constraints

- Python is pinned to 3.12 via `.python-version`; Node 24+ is used for the frontend.
- All API routes are under `/api/v1`, except `/health/live` and `/health/ready`.
- Access JWT TTL = 15 minutes; refresh token TTL = 7 days with rotation and family reuse detection.
- Refresh token is stored only as a SHA-256 hash and delivered as an `HttpOnly` cookie named `lexpilot_refresh`, path `/api/v1/auth`, `SameSite=Lax`; access token stays in frontend memory only.
- Login rate limit: 5 failures per 15 minutes per `(client IP, normalized email)`; successful login clears the counter.
- Every tenant-scoped query filters `tenant_id`; every protected endpoint checks current roles from the database.
- `POST /api/v1/admin/users` supports optional `Idempotency-Key`; records live 24 hours; same key + different payload returns 409.
- No secrets in source control. `.env` is ignored; `.env.example` contains placeholders only.
- Tests use PostgreSQL at `localhost:5432` database `lexpilot_test` and Redis at `localhost:6379/0` unless overridden by env.
- Use TDD: write the failing test, run it, implement, run it, commit.
- Each task ends with a commit. Do not batch tasks into one commit.
- Phase 0 does not include MinIO, Celery, contract upload, parsing, or review; those start in Phase 1.

---

## File Structure

```text
.
├── .env.example
├── .gitignore
├── .python-version
├── docker-compose.yml
├── docker/
│   └── postgres/init/01-create-test-db.sql
├── scripts/
│   └── e2e_backend.sh
├── .github/workflows/ci.yml
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/0001_initial.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── cli.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   ├── health.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       └── admin_users.py
│   │   ├── core/
│   │   │   ├── actor.py
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   └── security.py
│   │   ├── db/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── tenant.py
│   │   │       ├── user.py
│   │   │       ├── role_binding.py
│   │   │       ├── refresh_token.py
│   │   │       ├── resource_acl.py
│   │   │       └── idempotency.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   └── user.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── auth_service.py
│   │       ├── permission_service.py
│   │       ├── rate_limit.py
│   │       └── idempotency.py
│   └── tests/
│       ├── conftest.py
│       ├── test_health.py
│       ├── integration/
│       │   ├── test_schema_constraints.py
│       │   ├── test_auth_api.py
│       │   └── test_admin_users.py
│       └── unit/
│           ├── test_security.py
│           └── test_permissions.py
└── frontend/
    ├── package.json
    ├── package-lock.json
    ├── index.html
    ├── tsconfig.json
    ├── vite.config.ts
    ├── vitest.config.ts
    ├── eslint.config.js
    ├── playwright.config.ts
    ├── src/
    │   ├── main.ts
    │   ├── App.vue
    │   ├── style.css
    │   ├── router.ts
    │   ├── lib/
    │   │   ├── api.ts
    │   │   └── cn.ts
    │   ├── stores/auth.ts
    │   ├── components/ui/
    │   │   ├── Button.vue
    │   │   ├── Card.vue
    │   │   ├── Input.vue
    │   │   └── Label.vue
    │   └── pages/
    │       ├── LoginPage.vue
    │       └── DashboardPage.vue
    ├── src/stores/auth.spec.ts
    └── tests/e2e/login.spec.ts
```

---

### Task 1: Backend Scaffold, Config, Health Endpoints, Docker Infra

**Files:**
- Create: `.python-version`, `.gitignore`, `.env.example`
- Create: `docker-compose.yml`, `docker/postgres/init/01-create-test-db.sql`
- Create: `backend/pyproject.toml`, `backend/Dockerfile`
- Create: `backend/app/__init__.py`, `backend/app/main.py`
- Create: `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/core/logging.py`
- Create: `backend/app/api/__init__.py`, `backend/app/api/health.py`
- Create: `backend/tests/__init__.py`, `backend/tests/test_health.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `get_settings() -> Settings`, `create_app() -> FastAPI`, `GET /health/live`, `GET /health/ready`.

- [ ] **Step 1: Create the Python project and app skeleton**

`.python-version`:

```text
3.12
```

`.gitignore`:

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
.mypy_cache/
.pytest_cache/
.ruff_cache/
.coverage
htmlcov/

# Frontend
frontend/node_modules/
frontend/dist/
frontend/playwright-report/
frontend/test-results/

# Env & local data
.env
*.local
.DS_Store
```

`.env.example`:

```dotenv
ENV=dev
DATABASE_URL=postgresql+psycopg://lexpilot:lexpilot@localhost:5432/lexpilot
TEST_DATABASE_URL=postgresql+psycopg://lexpilot:lexpilot@localhost:5432/lexpilot_test
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=replace-with-a-long-random-secret
JWT_ACTIVE_KID=v1
JWT_KEYS={}
CORS_ORIGINS=["http://localhost:5173","http://localhost:4173","http://127.0.0.1:4173"]
COOKIE_SECURE=false
LOGIN_RATE_LIMIT=5
LOGIN_RATE_WINDOW_SECONDS=900
```

`backend/pyproject.toml`:

```toml
[project]
name = "lexpilot"
version = "0.1.0"
description = "LexPilot contract review agent"
requires-python = ">=3.12,<3.14"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn[standard]>=0.30,<1",
  "pydantic>=2.9,<3",
  "pydantic-settings>=2.5,<3",
  "sqlalchemy>=2.0.35,<3",
  "psycopg[binary]>=3.2,<4",
  "alembic>=1.13,<2",
  "pyjwt>=2.9,<3",
  "argon2-cffi>=23.1,<26",
  "redis>=5.0,<7",
  "email-validator>=2.2,<3",
  "typer>=0.12,<1",
  "uuid6>=2024.7.10",
]

[dependency-groups]
dev = [
  "pytest>=8.3,<9",
  "pytest-cov>=5,<7",
  "httpx>=0.27,<1",
  "fakeredis>=2.23,<3",
  "ruff>=0.6,<1",
  "mypy>=1.11,<2",
]

[tool.uv]
package = false

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.12"
check_untyped_defs = true
ignore_missing_imports = true
plugins = ["pydantic.mypy"]
```

Create empty `__init__.py` files in `backend/app`, `backend/app/api`, `backend/app/core`, `backend/tests`.

- [ ] **Step 2: Write the failing health test**

`backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_live_health_returns_ok() -> None:
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run the test and verify it fails**

Run from `backend/`:

```bash
uv sync
uv run pytest tests/test_health.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'` (or import error) because the app does not exist yet.

- [ ] **Step 4: Implement config, logging, health, and app factory**

`backend/app/core/config.py`:

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "dev"
    database_url: str = "postgresql+psycopg://lexpilot:lexpilot@localhost:5432/lexpilot"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_active_kid: str = "v1"
    jwt_keys: dict[str, str] = Field(default_factory=dict)
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    refresh_cookie_name: str = "lexpilot_refresh"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]
    login_rate_limit: int = 5
    login_rate_window_seconds: int = 900

    @property
    def jwt_keyring(self) -> dict[str, str]:
        return self.jwt_keys or {self.jwt_active_kid: self.jwt_secret}


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`backend/app/core/logging.py`:

```python
import logging


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
```

`backend/app/api/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready() -> dict[str, str]:
    return {"status": "ok"}
```

`backend/app/main.py`:

```python
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="LexPilot", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router, tags=["health"])

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid4().hex)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    return app


app = create_app()
```

- [ ] **Step 5: Run the test and verify it passes**

Run from `backend/`:

```bash
uv run pytest tests/test_health.py -v
```

Expected: `1 passed`.

- [ ] **Step 6: Add Docker infrastructure and backend Dockerfile**

`docker-compose.yml`:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: lexpilot
      POSTGRES_PASSWORD: lexpilot
      POSTGRES_DB: lexpilot
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U lexpilot -d lexpilot"]
      interval: 3s
      timeout: 3s
      retries: 20

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 3s
      timeout: 3s
      retries: 20

  api:
    build: ./backend
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+psycopg://lexpilot:lexpilot@postgres:5432/lexpilot
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pgdata:
```

`docker/postgres/init/01-create-test-db.sql`:

```sql
CREATE DATABASE lexpilot_test OWNER lexpilot;
```

`backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 7: Generate the lockfile, validate Compose, and run the test**

From repository root:

```bash
cd backend
uv lock
uv sync
uv run pytest tests/test_health.py -v
cd ..
docker compose config >/dev/null
```

Expected: lockfile created; `1 passed`; `docker compose config` exits 0 with no output.

- [ ] **Step 8: Commit**

```bash
git add .python-version .gitignore .env.example docker-compose.yml docker backend
git commit -m "chore: scaffold backend, config, health endpoints, docker infra"
```

---

### Task 2: Database Models, Initial Migration, Test Fixtures

**Files:**
- Create: `backend/app/db/__init__.py`, `backend/app/db/base.py`, `backend/app/db/session.py`
- Create: `backend/app/db/models/__init__.py`
- Create: `backend/app/db/models/tenant.py`
- Create: `backend/app/db/models/user.py`
- Create: `backend/app/db/models/role_binding.py`
- Create: `backend/app/db/models/refresh_token.py`
- Create: `backend/app/db/models/resource_acl.py`
- Create: `backend/app/db/models/idempotency.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/0001_initial.py`
- Create: `backend/tests/conftest.py`, `backend/tests/integration/__init__.py`, `backend/tests/integration/test_schema_constraints.py`

**Interfaces:**
- Consumes: `get_settings()`, `Settings.database_url`.
- Produces: `Base`, `get_db()`, `SessionLocal`, models `Tenant`, `User`, `RoleBinding`, `RefreshToken`, `ResourceAcl`, `IdempotencyKey`.

- [ ] **Step 1: Write the schema constraint tests**

`backend/tests/conftest.py` (initial version):

```python
import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://lexpilot:lexpilot@localhost:5432/lexpilot_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("COOKIE_SECURE", "false")

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import SessionLocal, engine


@pytest.fixture(scope="session", autouse=True)
def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


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
```

`backend/tests/integration/test_schema_constraints.py`:

```python
import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models import RoleBinding, Tenant, User


def test_duplicate_tenant_slug_is_rejected(db) -> None:
    db.add(Tenant(slug="acme", name="Acme"))
    db.commit()
    db.add(Tenant(slug="acme", name="Other"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_duplicate_role_binding_is_rejected(db) -> None:
    tenant = Tenant(slug="acme", name="Acme")
    user = User(email="a@example.com", password_hash="x", display_name="A")
    db.add_all([tenant, user])
    db.flush()
    db.add(RoleBinding(tenant_id=tenant.id, user_id=user.id, role="admin"))
    db.commit()
    db.add(RoleBinding(tenant_id=tenant.id, user_id=user.id, role="admin"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
```

- [ ] **Step 2: Run tests and verify they fail**

```bash
cd backend
uv run pytest tests/integration/test_schema_constraints.py -v
```

Expected: FAIL because `app.db.base` / models do not exist.

- [ ] **Step 3: Implement DB base and models**

`backend/app/db/base.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
```

`backend/app/db/session.py`:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
```

`backend/app/db/models/tenant.py`:

```python
from uuid import UUID

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"
    __table_args__ = (
        CheckConstraint("status IN ('active','disabled')", name="ck_tenants_status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
```

`backend/app/db/models/user.py`:

```python
from uuid import UUID

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
```

`backend/app/db/models/role_binding.py`:

```python
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin

ROLES = ("admin", "legal_reviewer", "business_submitter")


class RoleBinding(Base, TimestampMixin):
    __tablename__ = "role_bindings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "role", name="uq_role_bindings_tenant_user_role"),
        CheckConstraint(
            "role IN ('admin','legal_reviewer','business_submitter')",
            name="ck_role_bindings_role",
        ),
        Index("ix_role_bindings_tenant_user", "tenant_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    role: Mapped[str] = mapped_column(String(32), nullable=False)
```

`backend/app/db/models/refresh_token.py`:

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_tenant", "user_id", "tenant_id"),
        Index("ix_refresh_tokens_family", "family_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    family_id: Mapped[UUID] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("refresh_tokens.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

`backend/app/db/models/resource_acl.py`:

```python
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from app.db.base import Base, TimestampMixin


class ResourceAcl(Base, TimestampMixin):
    __tablename__ = "resource_acl"
    __table_args__ = (
        CheckConstraint(
            "(subject_type = 'user' AND user_id IS NOT NULL AND role IS NULL) OR "
            "(subject_type = 'role' AND role IS NOT NULL AND user_id IS NULL)",
            name="ck_resource_acl_subject",
        ),
        Index(
            "ix_resource_acl_resource",
            "tenant_id",
            "resource_type",
            "resource_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid7)
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"))
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[UUID] = mapped_column(nullable=False)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str | None] = mapped_column(String(32))
    permission: Mapped[str] = mapped_column(String(32), nullable=False)
```

`backend/app/db/models/idempotency.py`:

```python
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    tenant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

`backend/app/db/models/__init__.py`:

```python
from app.db.models.idempotency import IdempotencyKey
from app.db.models.refresh_token import RefreshToken
from app.db.models.resource_acl import ResourceAcl
from app.db.models.role_binding import ROLES, RoleBinding
from app.db.models.tenant import Tenant
from app.db.models.user import User

__all__ = [
    "IdempotencyKey",
    "RefreshToken",
    "ResourceAcl",
    "ROLES",
    "RoleBinding",
    "Tenant",
    "User",
]
```

- [ ] **Step 4: Configure Alembic and create the initial migration**

`backend/alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

`backend/alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base
import app.db.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

`backend/alembic/versions/0001_initial.py`:

```python
"""initial phase 0 schema

Revision ID: 0001
Revises:
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('active','disabled')", name="ck_tenants_status"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "role_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "role IN ('admin','legal_reviewer','business_submitter')",
            name="ck_role_bindings_role",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", "role", name="uq_role_bindings_tenant_user_role"),
    )
    op.create_index("ix_role_bindings_tenant_user", "role_bindings", ["tenant_id", "user_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["refresh_tokens.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_tenant", "refresh_tokens", ["user_id", "tenant_id"])
    op.create_index("ix_refresh_tokens_family", "refresh_tokens", ["family_id"])

    op.create_table(
        "resource_acl",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("subject_type", sa.String(length=16), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=True),
        sa.Column("permission", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "(subject_type = 'user' AND user_id IS NOT NULL AND role IS NULL) OR "
            "(subject_type = 'role' AND role IS NOT NULL AND user_id IS NULL)",
            name="ck_resource_acl_subject",
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resource_acl_resource",
        "resource_acl",
        ["tenant_id", "resource_type", "resource_id"],
    )

    op.create_table(
        "idempotency_keys",
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tenant_id", "key"),
    )


def downgrade() -> None:
    op.drop_table("idempotency_keys")
    op.drop_index("ix_resource_acl_resource", table_name="resource_acl")
    op.drop_table("resource_acl")
    op.drop_index("ix_refresh_tokens_family", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_tenant", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("ix_role_bindings_tenant_user", table_name="role_bindings")
    op.drop_table("role_bindings")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")
```

- [ ] **Step 5: Start infrastructure, run migrations, run tests**

From repository root:

```bash
docker compose up -d postgres redis
cd backend
uv run alembic upgrade head
uv run pytest tests/integration/test_schema_constraints.py -v
```

Expected: migrations apply; `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/db backend/alembic backend/alembic.ini backend/tests/conftest.py backend/tests/integration
git commit -m "feat: add phase 0 database models and initial migration"
```

---

### Task 3: Auth Primitives (Passwords, JWT, Refresh Rotation)

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/services/auth_service.py`, `backend/app/services/__init__.py`
- Create: `backend/tests/unit/__init__.py`, `backend/tests/unit/test_security.py`
- Create: `backend/tests/integration/test_refresh_tokens.py`

**Interfaces:**
- Consumes: `Session`, models `User`, `Tenant`, `RoleBinding`, `RefreshToken`.
- Produces: `hash_password`, `verify_password`, `create_access_token`, `decode_access_token`, `AuthResult`, `AuthError`, `RefreshTokenReuse`, `authenticate`, `create_refresh_token`, `rotate_refresh_token`, `revoke_refresh_token`.

- [ ] **Step 1: Write failing security tests**

`backend/tests/unit/test_security.py`:

```python
from uuid import uuid4

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
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
    user_id = uuid4()
    tenant_id = uuid4()
    token = create_access_token(user_id=user_id, tenant_id=tenant_id, roles=["admin"])
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token, forced_kid="missing")
```

- [ ] **Step 2: Run tests and verify they fail**

```bash
cd backend
uv run pytest tests/unit/test_security.py -v
```

Expected: FAIL because `app.core.security` does not exist.

- [ ] **Step 3: Implement security helpers**

`backend/app/core/security.py`:

```python
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import get_settings

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, ValueError):
        return False


def create_access_token(
    *, user_id: UUID, tenant_id: UUID, roles: list[str]
) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
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
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Write failing refresh rotation tests**

`backend/tests/integration/test_refresh_tokens.py`:

```python
import pytest

from app.core.security import hash_password
from app.db.models import RefreshToken, RoleBinding, Tenant, User
from app.services.auth_service import RefreshTokenReuse, create_refresh_token, rotate_refresh_token


def seed_user(db):
    tenant = Tenant(slug="acme", name="Acme")
    user = User(email="a@example.com", password_hash=hash_password("Secret123!"), display_name="A")
    db.add_all([tenant, user])
    db.flush()
    db.add(RoleBinding(tenant_id=tenant.id, user_id=user.id, role="admin"))
    db.commit()
    return tenant, user


def test_refresh_rotation_and_reuse_detection(db) -> None:
    tenant, user = seed_user(db)
    raw = create_refresh_token(db, user_id=user.id, tenant_id=tenant.id)
    new_raw, _, _ = rotate_refresh_token(db, raw)
    assert new_raw != raw
    with pytest.raises(RefreshTokenReuse):
        rotate_refresh_token(db, raw)
    db.rollback()
    revoked = db.query(RefreshToken).filter(RefreshToken.revoked_at.is_not(None)).all()
    assert revoked
```

- [ ] **Step 5: Implement auth service**

`backend/app/services/auth_service.py`:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session
from uuid6 import uuid7

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.db.models import RefreshToken, RoleBinding, Tenant, User


class AuthError(Exception):
    code = "AUTH_ERROR"
    status_code = 401

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)
        self.message = message


class InvalidCredentials(AuthError):
    code = "INVALID_CREDENTIALS"


class TenantSelectionRequired(AuthError):
    code = "TENANT_SELECTION_REQUIRED"
    status_code = 400

    def __init__(self, tenants: list[dict[str, str]]) -> None:
        super().__init__("Tenant selection required")
        self.tenants = tenants


class MembershipNotFound(AuthError):
    code = "MEMBERSHIP_NOT_FOUND"
    status_code = 403


class RefreshTokenInvalid(AuthError):
    code = "REFRESH_TOKEN_INVALID"


class RefreshTokenReuse(AuthError):
    code = "REFRESH_TOKEN_REUSE"
    status_code = 401


@dataclass(frozen=True)
class AuthResult:
    access_token: str
    refresh_token: str
    user: User
    tenant: Tenant
    roles: list[str]


def _memberships(db: Session, user_id: UUID) -> list[tuple[RoleBinding, Tenant]]:
    rows = db.execute(
        select(RoleBinding, Tenant)
        .join(Tenant, Tenant.id == RoleBinding.tenant_id)
        .where(RoleBinding.user_id == user_id, Tenant.status == "active")
        .order_by(Tenant.slug)
    ).all()
    return list(rows)


def roles_for(db: Session, user_id: UUID, tenant_id: UUID) -> list[str]:
    return list(
        db.scalars(
            select(RoleBinding.role).where(
                RoleBinding.user_id == user_id, RoleBinding.tenant_id == tenant_id
            )
        ).all()
    )


def authenticate(
    db: Session, *, email: str, password: str, tenant_slug: str | None = None
) -> AuthResult:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    memberships = _memberships(db, user.id)
    if not memberships:
        raise MembershipNotFound()
    if tenant_slug:
        matching = [(binding, tenant) for binding, tenant in memberships if tenant.slug == tenant_slug]
        if not matching:
            raise MembershipNotFound()
    elif len(memberships) > 1:
        raise TenantSelectionRequired(
            [{"slug": tenant.slug, "name": tenant.name} for _, tenant in memberships]
        )
    else:
        matching = memberships
    _, tenant = matching[0]
    roles = roles_for(db, user.id, tenant.id)
    refresh_token = create_refresh_token(db, user_id=user.id, tenant_id=tenant.id)
    access_token = create_access_token(user_id=user.id, tenant_id=tenant.id, roles=roles)
    return AuthResult(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user,
        tenant=tenant,
        roles=roles,
    )


def create_refresh_token(db: Session, *, user_id: UUID, tenant_id: UUID) -> str:
    settings = get_settings()
    raw = generate_refresh_token()
    now = datetime.now(timezone.utc)
    row = RefreshToken(
        user_id=user_id,
        tenant_id=tenant_id,
        token_hash=hash_refresh_token(raw),
        family_id=uuid7(),
        expires_at=now + timedelta(days=settings.refresh_token_days),
    )
    db.add(row)
    db.commit()
    return raw


def rotate_refresh_token(db: Session, raw: str) -> tuple[str, User, Tenant]:
    now = datetime.now(timezone.utc)
    row = db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw))
        .with_for_update()
    ).scalar_one_or_none()
    if row is None or row.expires_at <= now:
        raise RefreshTokenInvalid()
    if row.revoked_at is not None:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        db.commit()
        raise RefreshTokenReuse()
    user = db.get(User, row.user_id)
    tenant = db.get(Tenant, row.tenant_id)
    if user is None or tenant is None or not user.is_active or tenant.status != "active":
        raise RefreshTokenInvalid()
    new_raw = generate_refresh_token()
    new_row = RefreshToken(
        user_id=row.user_id,
        tenant_id=row.tenant_id,
        token_hash=hash_refresh_token(new_raw),
        family_id=row.family_id,
        expires_at=now + timedelta(days=get_settings().refresh_token_days),
    )
    db.add(new_row)
    db.flush()
    row.revoked_at = now
    row.replaced_by_id = new_row.id
    db.commit()
    return new_raw, user, tenant


def revoke_refresh_token(db: Session, raw: str) -> None:
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()


def switch_tenant(db: Session, raw: str, tenant_slug: str) -> AuthResult:
    now = datetime.now(timezone.utc)
    row = db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw))
        .with_for_update()
    ).scalar_one_or_none()
    if row is None or row.expires_at <= now or row.revoked_at is not None:
        raise RefreshTokenInvalid()
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise RefreshTokenInvalid()
    memberships = _memberships(db, user.id)
    matching = [(binding, tenant) for binding, tenant in memberships if tenant.slug == tenant_slug]
    if not matching:
        raise MembershipNotFound()
    _, tenant = matching[0]
    row.revoked_at = now
    roles = roles_for(db, user.id, tenant.id)
    new_refresh = create_refresh_token(db, user_id=user.id, tenant_id=tenant.id)
    access = create_access_token(user_id=user.id, tenant_id=tenant.id, roles=roles)
    return AuthResult(access, new_refresh, user, tenant, roles)
```

- [ ] **Step 6: Run tests and verify they pass**

```bash
cd backend
uv run pytest tests/unit/test_security.py tests/integration/test_refresh_tokens.py -v
```

Expected: `4 passed` (or all listed tests pass).

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/security.py backend/app/services backend/tests/unit backend/tests/integration/test_refresh_tokens.py
git commit -m "feat: add password, jwt, and refresh token primitives"
```

---

### Task 4: Auth API, Rate Limiting, Current User Dependency

**Files:**
- Create: `backend/app/core/actor.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/services/rate_limit.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/v1/__init__.py`, `backend/app/api/v1/auth.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/health.py` (real dependency checks for readiness)
- Create: `backend/tests/integration/test_auth_api.py`
- Modify: `backend/tests/conftest.py` (add Redis override, client, factories)

**Interfaces:**
- Consumes: `authenticate`, `rotate_refresh_token`, `revoke_refresh_token`, `switch_tenant`, `decode_access_token`, models.
- Produces: `ActorContext`, `get_current_actor`, `require_roles`, `GET /api/v1/auth/me`, `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/switch-tenant`.

- [ ] **Step 1: Extend the test fixtures**

Replace `backend/tests/conftest.py` with:

```python
import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://lexpilot:lexpilot@localhost:5432/lexpilot_test",
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("COOKIE_SECURE", "false")

import fakeredis
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_redis
from app.core.security import hash_password
from app.db.base import Base
from app.db.models import RoleBinding, Tenant, User
from app.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def create_schema() -> None:
    Base.metadata.create_all(bind=engine)


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
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture()
def client(redis_client):
    app.dependency_overrides[get_redis] = lambda: redis_client
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def tenant_user(db):
    tenant = Tenant(slug="acme", name="Acme")
    user = User(
        email="admin@example.com",
        password_hash=hash_password("Admin123!"),
        display_name="Admin",
    )
    db.add_all([tenant, user])
    db.flush()
    db.add(RoleBinding(tenant_id=tenant.id, user_id=user.id, role="admin"))
    db.commit()
    return tenant, user
```

- [ ] **Step 2: Write failing auth API tests**

`backend/tests/integration/test_auth_api.py`:

```python
def test_login_returns_access_token_and_refresh_cookie(client, tenant_user) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!", "tenant_slug": "acme"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["tenant"]["slug"] == "acme"
    assert "lexpilot_refresh" in response.cookies


def test_login_rejects_wrong_password(client, tenant_user) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong", "tenant_slug": "acme"},
    )
    assert response.status_code == 401


def test_login_rate_limits_after_five_failures(client, tenant_user) -> None:
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong", "tenant_slug": "acme"},
        )
        assert response.status_code == 401
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong", "tenant_slug": "acme"},
    )
    assert response.status_code == 429


def test_me_requires_access_token(client, tenant_user) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!", "tenant_slug": "acme"},
    )
    token = login.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "admin@example.com"
    assert response.json()["roles"] == ["admin"]


def test_ready_health_checks_dependencies(client) -> None:
    assert client.get("/health/ready").status_code == 200


def test_refresh_rotates_cookie_and_old_token_reuse_revokes_family(client, tenant_user) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!", "tenant_slug": "acme"},
    )
    old_cookie = login.cookies["lexpilot_refresh"]
    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    new_cookie = refresh.cookies["lexpilot_refresh"]
    assert new_cookie != old_cookie
    client.cookies.set("lexpilot_refresh", old_cookie, path="/api/v1/auth")
    reused = client.post("/api/v1/auth/refresh")
    assert reused.status_code == 401
```

- [ ] **Step 3: Run tests and verify they fail**

```bash
cd backend
uv run pytest tests/integration/test_auth_api.py -v
```

Expected: FAIL because the auth routes and dependencies do not exist.

- [ ] **Step 4: Implement actor, dependencies, rate limiter, schemas, and auth router**

`backend/app/core/actor.py`:

```python
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ActorContext:
    user_id: UUID
    tenant_id: UUID
    email: str
    display_name: str
    tenant_slug: str
    tenant_name: str
    roles: frozenset[str]
```

`backend/app/services/rate_limit.py`:

```python
from redis import Redis


class RateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__("Too many login attempts")
        self.retry_after = retry_after


class LoginRateLimiter:
    def __init__(self, redis: Redis, limit: int, window_seconds: int) -> None:
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds

    @staticmethod
    def _key(ip: str, email: str) -> str:
        return f"login:fail:{ip}:{email.strip().lower()}"

    def check(self, ip: str, email: str) -> None:
        key = self._key(ip, email)
        count = int(self.redis.get(key) or 0)
        if count >= self.limit:
            raise RateLimited(int(self.redis.ttl(key) or self.window_seconds))

    def record_failure(self, ip: str, email: str) -> None:
        key = self._key(ip, email)
        count = self.redis.incr(key)
        if count == 1:
            self.redis.expire(key, self.window_seconds)

    def reset(self, ip: str, email: str) -> None:
        self.redis.delete(self._key(ip, email))
```

`backend/app/api/deps.py`:

```python
from collections.abc import Generator
from uuid import UUID

import redis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext
from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.models import RoleBinding, Tenant, User
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)


def get_redis() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def get_current_actor(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> ActorContext:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
        tenant_id = UUID(payload["tid"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    roles = frozenset(
        db.scalars(
            select(RoleBinding.role).where(
                RoleBinding.user_id == user_id, RoleBinding.tenant_id == tenant_id
            )
        ).all()
    )
    user = db.get(User, user_id)
    tenant = db.get(Tenant, tenant_id)
    if (
        not roles
        or user is None
        or not user.is_active
        or tenant is None
        or tenant.status != "active"
    ):
        raise HTTPException(status_code=401, detail="Invalid session")
    return ActorContext(
        user_id=user.id,
        tenant_id=tenant.id,
        email=user.email,
        display_name=user.display_name,
        tenant_slug=tenant.slug,
        tenant_name=tenant.name,
        roles=roles,
    )


def require_roles(*allowed: str):
    def dependency(actor: ActorContext = Depends(get_current_actor)) -> ActorContext:
        if not actor.roles.intersection(allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
            )
        return actor

    return dependency
```

Replace `backend/app/api/health.py` with real readiness checks:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_redis

router = APIRouter()


@router.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db), redis=Depends(get_redis)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
        redis.ping()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="not ready") from exc
    return {"status": "ok"}
```

`backend/app/schemas/auth.py`:

```python
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    tenant_slug: str | None = None


class TenantInfo(BaseModel):
    id: UUID
    slug: str
    name: str


class UserInfo(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
    tenant: TenantInfo
    roles: list[str]


class MeResponse(BaseModel):
    user: UserInfo
    tenant: TenantInfo
    roles: list[str]


class SwitchTenantRequest(BaseModel):
    tenant_slug: str
```

`backend/app/api/v1/auth.py`:

```python
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_actor, get_db, get_redis
from app.core.actor import ActorContext
from app.core.config import get_settings
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    SwitchTenantRequest,
    TenantInfo,
    TokenResponse,
    UserInfo,
)
from app.core.security import create_access_token
from app.services.auth_service import (
    AuthError,
    AuthResult,
    authenticate,
    revoke_refresh_token,
    roles_for,
    rotate_refresh_token,
    switch_tenant,
)
from app.services.rate_limit import LoginRateLimiter, RateLimited

router = APIRouter(prefix="/auth", tags=["auth"])


def _response(result: AuthResult) -> TokenResponse:
    settings = get_settings()
    return TokenResponse(
        access_token=result.access_token,
        expires_in=settings.access_token_minutes * 60,
        user=UserInfo(id=result.user.id, email=result.user.email, display_name=result.user.display_name),
        tenant=TenantInfo(id=result.tenant.id, slug=result.tenant.slug, name=result.tenant.name),
        roles=result.roles,
    )


def _set_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/api/v1/auth",
        max_age=settings.refresh_token_days * 86400,
    )


def _clear_cookie(response: Response) -> None:
    response.delete_cookie(
        key=get_settings().refresh_cookie_name, path="/api/v1/auth"
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    settings = get_settings()
    limiter = LoginRateLimiter(redis, settings.login_rate_limit, settings.login_rate_window_seconds)
    ip = request.client.host if request.client else "unknown"
    try:
        limiter.check(ip, payload.email)
    except RateLimited as exc:
        raise HTTPException(
            status_code=429,
            detail={"code": "RATE_LIMITED", "message": "Too many login attempts"},
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    try:
        result = authenticate(
            db, email=payload.email, password=payload.password, tenant_slug=payload.tenant_slug
        )
    except AuthError as exc:
        limiter.record_failure(ip, payload.email)
        detail = {"code": exc.code, "message": exc.message}
        if hasattr(exc, "tenants"):
            detail["tenants"] = exc.tenants
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc
    limiter.reset(ip, payload.email)
    _set_cookie(response, result.refresh_token)
    return _response(result)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="lexpilot_refresh"),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    try:
        new_raw, user, tenant = rotate_refresh_token(db, refresh_token)
    except AuthError as exc:
        _clear_cookie(response)
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    roles = roles_for(db, user.id, tenant.id)
    result = AuthResult(
        access_token=create_access_token(
            user_id=user.id, tenant_id=tenant.id, roles=roles
        ),
        refresh_token=new_raw,
        user=user,
        tenant=tenant,
        roles=roles,
    )
    _set_cookie(response, new_raw)
    return _response(result)


@router.post("/logout", status_code=204)
def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="lexpilot_refresh"),
    db: Session = Depends(get_db),
) -> Response:
    if refresh_token:
        revoke_refresh_token(db, refresh_token)
    _clear_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=MeResponse)
def me(actor: ActorContext = Depends(get_current_actor)) -> MeResponse:
    return MeResponse(
        user=UserInfo(
            id=actor.user_id, email=actor.email, display_name=actor.display_name
        ),
        tenant=TenantInfo(id=actor.tenant_id, slug=actor.tenant_slug, name=actor.tenant_name),
        roles=sorted(actor.roles),
    )


@router.post("/switch-tenant", response_model=TokenResponse)
def switch(
    payload: SwitchTenantRequest,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="lexpilot_refresh"),
    db: Session = Depends(get_db),
) -> TokenResponse:
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    try:
        result = switch_tenant(db, refresh_token, payload.tenant_slug)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"code": exc.code}) from exc
    _set_cookie(response, result.refresh_token)
    return _response(result)
```

Modify `backend/app/main.py` to include the auth router:

```python
from app.api.v1.auth import router as auth_router
...
    app.include_router(auth_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests and fix implementation issues**

```bash
cd backend
uv run pytest tests/integration/test_auth_api.py -v
```

Expected: all auth API tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/actor.py backend/app/api backend/app/services/rate_limit.py backend/app/schemas backend/tests/conftest.py backend/tests/integration/test_auth_api.py
git commit -m "feat: add jwt auth api with refresh rotation and login rate limiting"
```

---

### Task 5: RBAC + ACL, Admin Users, Idempotency, Seed CLI

**Files:**
- Create: `backend/app/services/permission_service.py`
- Create: `backend/app/services/idempotency.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/api/v1/admin_users.py`
- Create: `backend/app/cli.py`
- Create: `backend/tests/unit/test_permissions.py`
- Create: `backend/tests/integration/test_admin_users.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `ActorContext`, `require_roles`, `get_db`, `ResourceAcl`, `IdempotencyKey`, `RoleBinding`, `User`, `Tenant`.
- Produces: `PermissionService.authorize`, `AdminUserCreate`, `GET /api/v1/admin/users`, `POST /api/v1/admin/users`, CLI `create-tenant`, `create-admin`, `seed-dev`.

- [ ] **Step 1: Write failing permission tests**

`backend/tests/unit/test_permissions.py`:

```python
from uuid import uuid4

import pytest

from app.core.actor import ActorContext
from app.services.permission_service import PermissionDenied, PermissionService


def actor(role: str) -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        email="x@example.com",
        display_name="X",
        tenant_slug="acme",
        tenant_name="Acme",
        roles=frozenset({role}),
    )


def test_admin_can_manage_users(db) -> None:
    PermissionService(db).authorize(actor("admin"), "user:manage")


def test_submitter_cannot_manage_users(db) -> None:
    with pytest.raises(PermissionDenied):
        PermissionService(db).authorize(actor("business_submitter"), "user:manage")


def test_acl_grant_and_deny(db) -> None:
    from app.db.models import ResourceAcl, Tenant

    tenant = Tenant(slug="acme", name="Acme")
    db.add(tenant)
    db.flush()
    resource_id = uuid4()

    class Resource:
        tenant_id = tenant.id
        resource_type = "contract"
        resource_id = resource_id

    a = ActorContext(
        user_id=uuid4(),
        tenant_id=tenant.id,
        email="u@example.com",
        display_name="U",
        tenant_slug="acme",
        tenant_name="Acme",
        roles=frozenset({"legal_reviewer"}),
    )
    service = PermissionService(db)
    service.authorize(a, "contract:read", Resource())

    db.add(
        ResourceAcl(
            tenant_id=tenant.id,
            resource_type="contract",
            resource_id=resource_id,
            subject_type="role",
            user_id=None,
            role="legal_reviewer",
            permission="deny",
        )
    )
    db.commit()
    with pytest.raises(PermissionDenied):
        service.authorize(a, "contract:read", Resource())
```

- [ ] **Step 2: Implement permission service**

`backend/app/services/permission_service.py`:

```python
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.actor import ActorContext
from app.db.models import ResourceAcl

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {"*"},
    "legal_reviewer": {
        "user:read",
        "contract:read",
        "review:read",
        "review:write",
        "human_review:submit",
        "knowledge:read",
    },
    "business_submitter": {
        "contract:create",
        "contract:read",
        "review:read",
    },
}


class PermissionDenied(Exception):
    pass


class ResourceRef:
    tenant_id: object
    resource_type: str
    resource_id: object


class PermissionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def authorize(
        self, actor: ActorContext, permission: str, resource: ResourceRef | None = None
    ) -> None:
        if resource is not None and resource.tenant_id != actor.tenant_id:
            raise PermissionDenied()
        roles = ROLE_PERMISSIONS
        if "admin" in actor.roles:
            return
        if resource is not None:
            acl = self.db.scalars(
                select(ResourceAcl).where(
                    ResourceAcl.tenant_id == actor.tenant_id,
                    ResourceAcl.resource_type == resource.resource_type,
                    ResourceAcl.resource_id == resource.resource_id,
                    or_(
                        (ResourceAcl.subject_type == "user")
                        & (ResourceAcl.user_id == actor.user_id),
                        (ResourceAcl.subject_type == "role")
                        & (ResourceAcl.role.in_(actor.roles)),
                    ),
                )
            ).all()
            if acl:
                if any(entry.permission == "deny" for entry in acl):
                    raise PermissionDenied()
                if any(entry.permission in {permission, "admin"} for entry in acl):
                    return
                raise PermissionDenied()
        allowed = any(
            permission in roles.get(role, set()) or "*" in roles.get(role, set())
            for role in actor.roles
        )
        if not allowed:
            raise PermissionDenied()
```

- [ ] **Step 3: Write failing admin/idempotency tests**

`backend/tests/integration/test_admin_users.py`:

```python
def login_admin(client) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Admin123!", "tenant_slug": "acme"},
    )
    return response.json()["access_token"]


def test_admin_can_create_and_list_users(client, tenant_user) -> None:
    token = login_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "email": "reviewer@example.com",
            "password": "Reviewer123!",
            "display_name": "Reviewer",
            "role": "legal_reviewer",
        },
    )
    assert created.status_code == 201
    listed = client.get("/api/v1/admin/users", headers=headers)
    assert listed.status_code == 200
    assert {item["email"] for item in listed.json()} == {
        "admin@example.com",
        "reviewer@example.com",
    }


def test_non_admin_cannot_list_users(client, tenant_user, db) -> None:
    from app.core.security import hash_password
    from app.db.models import RoleBinding, User

    user = User(
        email="submitter@example.com",
        password_hash=hash_password("Submitter123!"),
        display_name="Submitter",
    )
    db.add(user)
    db.flush()
    db.add(
        RoleBinding(
            tenant_id=tenant_user[0].id, user_id=user.id, role="business_submitter"
        )
    )
    db.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "submitter@example.com",
            "password": "Submitter123!",
            "tenant_slug": "acme",
        },
    )
    token = login.json()["access_token"]
    response = client.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_admin_user_creation_is_idempotent(client, tenant_user) -> None:
    token = login_admin(client)
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "create-reviewer-1"}
    payload = {
        "email": "reviewer@example.com",
        "password": "Reviewer123!",
        "display_name": "Reviewer",
        "role": "legal_reviewer",
    }
    first = client.post("/api/v1/admin/users", headers=headers, json=payload)
    second = client.post("/api/v1/admin/users", headers=headers, json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    conflict = client.post(
        "/api/v1/admin/users",
        headers={**headers, "Idempotency-Key": "create-reviewer-1"},
        json={**payload, "display_name": "Other"},
    )
    assert conflict.status_code == 409
```

- [ ] **Step 4: Implement idempotency service, schemas, admin router, CLI**

`backend/app/services/idempotency.py`:

```python
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import IdempotencyKey


class IdempotencyConflict(Exception):
    pass


def request_hash(payload: Any) -> str:
    import json

    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class IdempotencyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, tenant_id: UUID, key: str, payload_hash: str) -> IdempotencyKey | None:
        row = self.db.get(IdempotencyKey, (tenant_id, key))
        if row is None:
            return None
        if row.expires_at <= datetime.now(timezone.utc):
            self.db.delete(row)
            self.db.commit()
            return None
        if row.request_hash != payload_hash:
            raise IdempotencyConflict()
        return row

    def save(
        self,
        tenant_id: UUID,
        key: str,
        payload_hash: str,
        status: int,
        body: dict[str, Any],
    ) -> None:
        self.db.add(
            IdempotencyKey(
                tenant_id=tenant_id,
                key=key,
                request_hash=payload_hash,
                response_status=status,
                response_body=body,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            )
        )
```

`backend/app/schemas/user.py`:

```python
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.db.models.role_binding import ROLES


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)
    display_name: str = Field(min_length=1, max_length=255)
    role: str

    def model_post_init(self, __context) -> None:
        if self.role not in ROLES:
            raise ValueError("invalid role")


class AdminUserRead(BaseModel):
    id: UUID
    email: EmailStr
    display_name: str
    roles: list[str]
```

`backend/app/api/v1/admin_users.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.actor import ActorContext
from app.core.security import hash_password
from app.db.models import RoleBinding, User
from app.schemas.user import AdminUserCreate, AdminUserRead
from app.services.idempotency import IdempotencyConflict, IdempotencyService, request_hash

router = APIRouter(prefix="/admin/users", tags=["admin-users"], dependencies=[Depends(require_roles("admin"))])


def _user_read(db: Session, user: User, tenant_id) -> AdminUserRead:
    roles = sorted(
        db.scalars(
            select(RoleBinding.role).where(
                RoleBinding.user_id == user.id, RoleBinding.tenant_id == tenant_id
            )
        ).all()
    )
    return AdminUserRead(id=user.id, email=user.email, display_name=user.display_name, roles=roles)


@router.get("", response_model=list[AdminUserRead])
def list_users(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(require_roles("admin")),
) -> list[AdminUserRead]:
    users = db.scalars(
        select(User)
        .join(RoleBinding, RoleBinding.user_id == User.id)
        .where(RoleBinding.tenant_id == actor.tenant_id)
        .order_by(User.email)
    ).unique().all()
    return [_user_read(db, user, actor.tenant_id) for user in users]


@router.post("", response_model=AdminUserRead, status_code=201)
def create_user(
    payload: AdminUserCreate,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(require_roles("admin")),
):
    body = payload.model_dump(mode="json")
    payload_hash = request_hash(body)
    service = IdempotencyService(db)
    if idempotency_key:
        try:
            existing = service.get(actor.tenant_id, idempotency_key, payload_hash)
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=409, detail="Idempotency key conflict") from exc
        if existing is not None:
            return JSONResponse(
                status_code=existing.response_status, content=existing.response_body
            )
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(payload.password),
            display_name=payload.display_name,
        )
        db.add(user)
        db.flush()
    existing_binding = db.scalar(
        select(RoleBinding).where(
            RoleBinding.tenant_id == actor.tenant_id,
            RoleBinding.user_id == user.id,
            RoleBinding.role == payload.role,
        )
    )
    if existing_binding is not None:
        raise HTTPException(status_code=409, detail="User already has this role in tenant")
    db.add(
        RoleBinding(tenant_id=actor.tenant_id, user_id=user.id, role=payload.role)
    )
    db.flush()
    result = _user_read(db, user, actor.tenant_id)
    if idempotency_key:
        service.save(
            actor.tenant_id,
            idempotency_key,
            payload_hash,
            201,
            result.model_dump(mode="json"),
        )
    db.commit()
    return result
```

`backend/app/cli.py`:

```python
import typer
from sqlalchemy import select

from app.core.security import hash_password
from app.db.models import RoleBinding, Tenant, User
from app.db.session import SessionLocal

app = typer.Typer(help="LexPilot admin CLI")


@app.command("create-tenant")
def create_tenant(slug: str, name: str) -> None:
    with SessionLocal() as db:
        if db.scalar(select(Tenant).where(Tenant.slug == slug)):
            typer.echo("tenant already exists")
            raise typer.Exit(code=1)
        tenant = Tenant(slug=slug, name=name)
        db.add(tenant)
        db.commit()
        typer.echo(str(tenant.id))


@app.command("create-admin")
def create_admin(tenant_slug: str, email: str, password: str, display_name: str = "Administrator") -> None:
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
        if tenant is None:
            typer.echo("tenant not found")
            raise typer.Exit(code=1)
        user = db.scalar(select(User).where(User.email == email.lower()))
        if user is None:
            user = User(
                email=email.lower(),
                password_hash=hash_password(password),
                display_name=display_name,
            )
            db.add(user)
            db.flush()
        if db.scalar(
            select(RoleBinding).where(
                RoleBinding.tenant_id == tenant.id,
                RoleBinding.user_id == user.id,
                RoleBinding.role == "admin",
            )
        ):
            typer.echo("admin already exists")
            raise typer.Exit(code=1)
        db.add(RoleBinding(tenant_id=tenant.id, user_id=user.id, role="admin"))
        db.commit()
        typer.echo(str(user.id))


@app.command("seed-dev")
def seed_dev() -> None:
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == "acme"))
        if tenant is None:
            tenant = Tenant(slug="acme", name="Acme")
            db.add(tenant)
            db.flush()
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        if user is None:
            user = User(
                email="admin@example.com",
                password_hash=hash_password("Admin123!"),
                display_name="Admin",
            )
            db.add(user)
            db.flush()
        if not db.scalar(
            select(RoleBinding).where(
                RoleBinding.tenant_id == tenant.id,
                RoleBinding.user_id == user.id,
                RoleBinding.role == "admin",
            )
        ):
            db.add(RoleBinding(tenant_id=tenant.id, user_id=user.id, role="admin"))
        db.commit()
        typer.echo(f"tenant={tenant.slug} email={user.email}")


if __name__ == "__main__":
    app()
```

Modify `backend/app/main.py`:

```python
from app.api.v1.admin_users import router as admin_users_router
...
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(admin_users_router, prefix="/api/v1")
```

- [ ] **Step 5: Run tests and fix issues**

```bash
cd backend
uv run pytest tests/unit/test_permissions.py tests/integration/test_admin_users.py -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/permission_service.py backend/app/services/idempotency.py backend/app/schemas/user.py backend/app/api/v1/admin_users.py backend/app/cli.py backend/app/main.py backend/tests/unit/test_permissions.py backend/tests/integration/test_admin_users.py
git commit -m "feat: add rbac/acl, admin user api, idempotency, and seed cli"
```

---

### Task 6: Frontend Scaffold, Login, Dashboard, Route Guard

**Files:**
- Create: `frontend/package.json`, `frontend/package-lock.json`, `frontend/index.html`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/vitest.config.ts`, `frontend/eslint.config.js`
- Create: `frontend/src/main.ts`, `frontend/src/App.vue`, `frontend/src/style.css`, `frontend/src/vite-env.d.ts`, `frontend/src/router.ts`
- Create: `frontend/src/lib/api.ts`, `frontend/src/lib/cn.ts`, `frontend/src/stores/auth.ts`
- Create: `frontend/src/components/ui/Button.vue`, `Card.vue`, `Input.vue`, `Label.vue`
- Create: `frontend/src/pages/LoginPage.vue`, `DashboardPage.vue`
- Create: `frontend/src/stores/auth.spec.ts`

**Interfaces:**
- Consumes: `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`.
- Produces: login form, dashboard, route guard, auth store.

- [ ] **Step 1: Scaffold the Vue app and install dependencies**

```bash
cd frontend
npm init -y
npm install vue vue-router pinia class-variance-authority clsx tailwind-merge lucide-vue-next
npm install -D vite @vitejs/plugin-vue typescript vue-tsc tailwindcss @tailwindcss/vite vitest @vue/test-utils jsdom @playwright/test eslint @eslint/js eslint-plugin-vue typescript-eslint vue-eslint-parser @types/node globals
npx playwright install chromium
```

Replace `frontend/package.json` with:

```json
{
  "name": "lexpilot-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc --noEmit && vite build",
    "preview": "vite preview --host 127.0.0.1 --port 4173",
    "lint": "eslint .",
    "test:unit": "vitest run",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-vue-next": "^0.468.0",
    "pinia": "^3.0.1",
    "tailwind-merge": "^3.0.1",
    "vue": "^3.5.13",
    "vue-router": "^4.5.0"
  },
  "devDependencies": {
    "@eslint/js": "^9.17.0",
    "@playwright/test": "^1.50.1",
    "@types/node": "^24.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "@vitejs/plugin-vue": "^6.0.0",
    "@vue/test-utils": "^2.4.6",
    "eslint": "^9.17.0",
    "eslint-plugin-vue": "^9.32.0",
    "globals": "^15.14.0",
    "jsdom": "^26.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "~5.7.2",
    "typescript-eslint": "^8.19.0",
    "vite": "^7.0.0",
    "vitest": "^3.0.0",
    "vue-eslint-parser": "^10.0.0",
    "vue-tsc": "^2.2.0"
  }
}
```

- [ ] **Step 2: Add frontend configuration files**

`frontend/index.html`:

```html
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>LexPilot</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "jsx": "preserve",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "esModuleInterop": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "types": ["vitest/globals", "node"],
    "baseUrl": ".",
    "paths": { "@/*": ["./src/*"] },
    "skipLibCheck": true
  },
  "include": ["src/**/*.ts", "src/**/*.vue", "vite.config.ts", "vitest.config.ts"]
}
```

`frontend/vite.config.ts`:

```ts
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
})
```

`frontend/vitest.config.ts`:

```ts
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
```

`frontend/eslint.config.js`:

```js
import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  { ignores: ['dist', 'node_modules', 'playwright-report', 'test-results'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['src/**/*.{ts,vue}'],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { parser: tseslint.parser },
    },
    rules: { 'vue/multi-word-component-names': 'off' },
  },
  {
    files: ['*.config.{js,ts}', 'tests/**/*.ts'],
    languageOptions: { globals: globals.node },
  },
)
```

`frontend/src/style.css`:

```css
@import "tailwindcss";

body {
  @apply bg-slate-50 text-slate-900 antialiased;
}
```

`frontend/src/vite-env.d.ts`:

```ts
/// <reference types="vite/client" />
```

`frontend/src/lib/cn.ts`:

```ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 3: Add UI components and API/types**

`frontend/src/lib/api.ts`:

```ts
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export type ApiError = {
  detail?: string | { code?: string; message?: string }
}

export async function apiFetch(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  })
  if (!response.ok) {
    let body: ApiError = {}
    try {
      body = await response.json()
    } catch {
      // ignore non-json errors
    }
    throw new Error(
      typeof body.detail === 'string'
        ? body.detail
        : body.detail?.message ?? `Request failed (${response.status})`,
    )
  }
  return response
}
```

`frontend/src/components/ui/Button.vue`:

```vue
<script setup lang="ts">
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/cn'

const variants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-slate-900 text-white hover:bg-slate-700',
        outline: 'border border-slate-300 bg-white hover:bg-slate-100',
        ghost: 'hover:bg-slate-100',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

const props = defineProps<{
  variant?: VariantProps<typeof variants>['variant']
  size?: VariantProps<typeof variants>['size']
  type?: 'button' | 'submit' | 'reset'
}>()
</script>

<template>
  <button :type="props.type ?? 'button'" :class="cn(variants({ variant: props.variant, size: props.size }))">
    <slot />
  </button>
</template>
```

`frontend/src/components/ui/Input.vue`:

```vue
<script setup lang="ts">
import { cn } from '@/lib/cn'

defineProps<{ modelValue?: string; type?: string; placeholder?: string; autocomplete?: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <input
    :value="modelValue"
    :type="type ?? 'text'"
    :placeholder="placeholder"
    :autocomplete="autocomplete"
    :class="cn('flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-slate-500')"
    @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
  />
</template>
```

`frontend/src/components/ui/Label.vue`:

```vue
<template>
  <label class="text-sm font-medium text-slate-700"><slot /></label>
</template>
```

`frontend/src/components/ui/Card.vue`:

```vue
<template>
  <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
    <slot />
  </div>
</template>
```

- [ ] **Step 4: Add auth store, router, pages, and app entry**

`frontend/src/stores/auth.ts`:

```ts
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { API_BASE } from '@/lib/api'

export type UserInfo = { id: string; email: string; display_name: string }
export type TenantInfo = { id: string; slug: string; name: string }

type LoginResponse = {
  access_token: string
  user: UserInfo
  tenant: TenantInfo
  roles: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserInfo | null>(null)
  const tenant = ref<TenantInfo | null>(null)
  const roles = ref<string[]>([])
  const loading = ref(false)
  let refreshPromise: Promise<boolean> | null = null

  const isAuthenticated = computed(() => accessToken.value !== null)

  async function parse(response: Response): Promise<LoginResponse> {
    if (!response.ok) {
      let message = '登录失败'
      try {
        const body = await response.json()
        message = body.detail?.message ?? body.detail ?? message
      } catch {
        // ignore
      }
      throw new Error(message)
    }
    return (await response.json()) as LoginResponse
  }

  function apply(payload: LoginResponse) {
    accessToken.value = payload.access_token
    user.value = payload.user
    tenant.value = payload.tenant
    roles.value = payload.roles
  }

  async function login(email: string, password: string, tenantSlug?: string) {
    loading.value = true
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, tenant_slug: tenantSlug || null }),
      })
      apply(await parse(response))
    } finally {
      loading.value = false
    }
  }

  async function refresh(): Promise<boolean> {
    if (refreshPromise) return refreshPromise
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
        })
        if (!response.ok) return false
        apply((await response.json()) as LoginResponse)
        return true
      } catch {
        return false
      } finally {
        refreshPromise = null
      }
    })()
    return refreshPromise
  }

  async function logout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, { method: 'POST', credentials: 'include' })
    } finally {
      accessToken.value = null
      user.value = null
      tenant.value = null
      roles.value = []
    }
  }

  async function bootstrap() {
    return accessToken.value !== null ? true : refresh()
  }

  return { accessToken, user, tenant, roles, loading, isAuthenticated, login, refresh, logout, bootstrap }
})
```

`frontend/src/router.ts`:

```ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import LoginPage from '@/pages/LoginPage.vue'
import DashboardPage from '@/pages/DashboardPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: LoginPage },
    { path: '/', name: 'dashboard', component: DashboardPage, meta: { requiresAuth: true } },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth) {
    const ok = await auth.bootstrap()
    if (!ok) return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isAuthenticated) return { name: 'dashboard' }
  return true
})
```

`frontend/src/pages/LoginPage.vue`:

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'
import Input from '@/components/ui/Input.vue'
import Label from '@/components/ui/Label.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const email = ref('admin@example.com')
const password = ref('Admin123!')
const tenantSlug = ref('acme')
const error = ref('')

async function submit() {
  error.value = ''
  try {
    await auth.login(email.value, password.value, tenantSlug.value)
    await router.push((route.query.redirect as string) ?? '/')
  } catch (err) {
    error.value = err instanceof Error ? err.message : '登录失败'
  }
}
</script>

<template>
  <main class="flex min-h-screen items-center justify-center p-6">
    <Card class="w-full max-w-md">
      <h1 class="text-2xl font-semibold">LexPilot</h1>
      <p class="mt-1 text-sm text-slate-500">合同审查 Agent</p>
      <form class="mt-6 space-y-4" @submit.prevent="submit">
        <div class="space-y-2">
          <Label for="tenant">租户</Label>
          <Input id="tenant" v-model="tenantSlug" placeholder="acme" autocomplete="organization" />
        </div>
        <div class="space-y-2">
          <Label for="email">邮箱</Label>
          <Input id="email" v-model="email" type="email" autocomplete="email" />
        </div>
        <div class="space-y-2">
          <Label for="password">密码</Label>
          <Input id="password" v-model="password" type="password" autocomplete="current-password" />
        </div>
        <p v-if="error" class="text-sm text-red-600">{{ error }}</p>
        <Button type="submit" class="w-full" :disabled="auth.loading">
          {{ auth.loading ? '登录中…' : '登录' }}
        </Button>
      </form>
    </Card>
  </main>
</template>
```

`frontend/src/pages/DashboardPage.vue`:

```vue
<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import Button from '@/components/ui/Button.vue'
import Card from '@/components/ui/Card.vue'

const auth = useAuthStore()
const router = useRouter()

async function logout() {
  await auth.logout()
  await router.push('/login')
}
</script>

<template>
  <main class="mx-auto max-w-4xl p-8">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-semibold">LexPilot 工作台</h1>
        <p class="mt-1 text-sm text-slate-500">
          {{ auth.tenant?.name }} · {{ auth.user?.email }} · {{ auth.roles.join(', ') }}
        </p>
      </div>
      <Button variant="outline" @click="logout">退出登录</Button>
    </div>
    <Card class="mt-8">
      <h2 class="text-lg font-medium">Phase 0 已就绪</h2>
      <p class="mt-2 text-sm text-slate-600">
        认证、租户、角色与登录流程已接通。合同上传、解析与审查将在下一阶段实现。
      </p>
    </Card>
  </main>
</template>
```

`frontend/src/App.vue`:

```vue
<template>
  <router-view />
</template>
```

`frontend/src/main.ts`:

```ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import './style.css'

createApp(App).use(createPinia()).use(router).mount('#app')
```

- [ ] **Step 5: Write and run the auth store unit test**

`frontend/src/stores/auth.spec.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from './auth'

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('logs in and stores the session in memory', async () => {
    const payload = {
      access_token: 'access-1',
      user: { id: 'u1', email: 'admin@example.com', display_name: 'Admin' },
      tenant: { id: 't1', slug: 'acme', name: 'Acme' },
      roles: ['admin'],
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    )
    const auth = useAuthStore()
    await auth.login('admin@example.com', 'Admin123!', 'acme')
    expect(auth.isAuthenticated).toBe(true)
    expect(auth.user?.email).toBe('admin@example.com')
    expect(auth.roles).toEqual(['admin'])
  })

  it('bootstraps via refresh and clears on logout', async () => {
    const payload = {
      access_token: 'access-2',
      user: { id: 'u1', email: 'admin@example.com', display_name: 'Admin' },
      tenant: { id: 't1', slug: 'acme', name: 'Acme' },
      roles: ['admin'],
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(payload), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetchMock)
    const auth = useAuthStore()
    expect(await auth.bootstrap()).toBe(true)
    expect(auth.accessToken).toBe('access-2')
    await auth.logout()
    expect(auth.isAuthenticated).toBe(false)
  })
})
```

Run:

```bash
cd frontend
npm install
npx playwright install chromium
npm run test:unit
npm run lint
npm run build
```

Expected: unit tests pass, lint passes, production build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend
git commit -m "feat: add vue login, dashboard, auth store, and route guard"
```

---

### Task 7: E2E Login Test and GitHub Actions CI

**Files:**
- Create: `scripts/e2e_backend.sh`
- Create: `frontend/playwright.config.ts`
- Create: `frontend/tests/e2e/login.spec.ts`
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `uv run alembic upgrade head`, `uv run python -m app.cli seed-dev`, `uvicorn`, Vite dev server.
- Produces: one Playwright login test and CI jobs for backend, frontend, and E2E.

- [ ] **Step 1: Write the E2E backend startup script**

`scripts/e2e_backend.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${E2E_EXTERNAL_SERVICES:-0}" != "1" ]]; then
  docker compose up -d postgres redis
  until docker compose exec -T postgres pg_isready -U lexpilot -d lexpilot >/dev/null 2>&1; do
    sleep 1
  done
fi

export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://lexpilot:lexpilot@localhost:5432/lexpilot_test}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export JWT_SECRET="${JWT_SECRET:-e2e-secret}"
export COOKIE_SECURE=false

cd backend
uv run alembic upgrade head
uv run python -m app.cli seed-dev
exec uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Make it executable:

```bash
chmod +x scripts/e2e_backend.sh
```

- [ ] **Step 2: Write Playwright config and test**

`frontend/playwright.config.ts`:

```ts
import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:4173',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'bash ../scripts/e2e_backend.sh',
      url: 'http://localhost:8000/health/live',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: 'npm run dev -- --host localhost --port 4173',
      url: 'http://localhost:4173',
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
```

`frontend/tests/e2e/login.spec.ts`:

```ts
import { expect, test } from '@playwright/test'

test('admin can log in and see the dashboard', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('租户').fill('acme')
  await page.getByLabel('邮箱').fill('admin@example.com')
  await page.getByLabel('密码').fill('Admin123!')
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByText('LexPilot 工作台')).toBeVisible()
  await expect(page.getByText('admin@example.com')).toBeVisible()
})
```

- [ ] **Step 3: Run the E2E test locally**

Ensure Docker is running, then:

```bash
cd frontend
npm run test:e2e
```

Expected: `1 passed`.

- [ ] **Step 4: Add GitHub Actions CI**

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: lexpilot
          POSTGRES_PASSWORD: lexpilot
          POSTGRES_DB: lexpilot_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U lexpilot -d lexpilot_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 20
      redis:
        image: redis:7
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 20
    env:
      DATABASE_URL: postgresql+psycopg://lexpilot:lexpilot@localhost:5432/lexpilot_test
      REDIS_URL: redis://localhost:6379/0
      JWT_SECRET: ci-test-secret
      COOKIE_SECURE: "false"
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          version: "0.12.17"
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run mypy app
      - run: uv run alembic upgrade head
      - run: uv run pytest -q

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run test:unit
      - run: npm run build

  e2e:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: lexpilot
          POSTGRES_PASSWORD: lexpilot
          POSTGRES_DB: lexpilot_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U lexpilot -d lexpilot_test"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 20
      redis:
        image: redis:7
        ports: ["6379:6379"]
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 5s
          --health-timeout 5s
          --health-retries 20
    env:
      E2E_EXTERNAL_SERVICES: "1"
      DATABASE_URL: postgresql+psycopg://lexpilot:lexpilot@localhost:5432/lexpilot_test
      REDIS_URL: redis://localhost:6379/0
      JWT_SECRET: ci-e2e-secret
      COOKIE_SECURE: "false"
      CI: "true"
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          version: "0.12.17"
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: uv sync --frozen
        working-directory: backend
      - run: npm ci
        working-directory: frontend
      - run: npx playwright install --with-deps chromium
        working-directory: frontend
      - run: npm run test:e2e
        working-directory: frontend
```

- [ ] **Step 5: Validate YAML and run local checks**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
cd frontend && npm run test:e2e
```

Expected: YAML parses; E2E passes.

- [ ] **Step 6: Commit**

```bash
git add scripts/e2e_backend.sh frontend/playwright.config.ts frontend/tests/e2e .github/workflows/ci.yml
git commit -m "ci: add playwright login e2e and layered github actions pipeline"
```

---

### Task 8: README, Full Verification, and Phase 0 Acceptance

**Files:**
- Modify: `README.md`
- No new source files.

**Interfaces:**
- Consumes: all Phase 0 deliverables.
- Produces: documented setup/run/test commands and verified Phase 0.

- [ ] **Step 1: Update README with Phase 0 instructions**

Replace `README.md` with:

```markdown
# LexPilot

企业级合同审查 Agent —— 基于 FastAPI、LangGraph、PostgreSQL + pgvector 的 RAG 合同审查系统。

## 文档

- [系统设计规格](docs/superpowers/specs/2026-10-19-contract-review-agent-design.md)
- [Phase 0 实现计划](docs/superpowers/plans/2026-10-19-lexpilot-phase-0-foundation.md)

## 当前状态

Phase 0：认证、租户、RBAC/ACL、管理员用户管理、前端登录与 CI 已就绪。合同上传、解析、知识库与审查工作流在后续阶段实现。

## 本地开发

前置：Docker Desktop、uv、Node 24+。

```bash
cp .env.example .env
docker compose up -d postgres redis
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.cli seed-dev
uv run uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173 ，使用 `admin@example.com / Admin123!`、租户 `acme` 登录。

## 测试

```bash
cd backend
uv run ruff check .
uv run mypy app
uv run alembic upgrade head
uv run pytest

cd ../frontend
npm run lint
npm run test:unit
npm run build
npm run test:e2e
```

## 设计边界

- LLM 不独立决定法律风险；风险结论由确定性 Rules Engine 产生（Phase 3 实现）。
- 人工复核等待期间不占用 Celery Worker（Phase 3 实现）。
- 不提供自由问答，不拆微服务。
```

- [ ] **Step 2: Run the full Phase 0 verification**

From repository root:

```bash
docker compose up -d postgres redis
cd backend
uv run alembic upgrade head
uv run ruff check .
uv run mypy app
uv run pytest -q
cd ../frontend
npm run lint
npm run test:unit
npm run build
npm run test:e2e
cd ..
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
docker compose config >/dev/null
```

Expected:
- `ruff` reports no issues.
- `mypy` reports `Success: no issues found`.
- Backend tests all pass.
- Frontend lint, unit tests, and build pass.
- Playwright login test passes.
- YAML parses and Compose config is valid.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: document phase 0 setup, run, and verification"
```

---

## Phase 0 Acceptance Checklist

- [ ] `docker compose up -d postgres redis` works.
- [ ] `uv run alembic upgrade head` applies all tables.
- [ ] A seeded admin can log in with tenant `acme`.
- [ ] Access token is required for `/api/v1/auth/me` and admin endpoints.
- [ ] Refresh rotation works; reused old refresh revokes the family.
- [ ] Login rate limiting returns 429 after 5 failures.
- [ ] Non-admin receives 403 on admin endpoints.
- [ ] Cross-tenant access is denied (permission service test).
- [ ] Admin user creation is idempotent and conflicts on different payloads.
- [ ] Vue login → dashboard → logout works.
- [ ] Playwright login E2E passes.
- [ ] CI runs backend lint/type/tests, frontend lint/unit/build, and E2E.
- [ ] No secrets committed; `.env` ignored.
