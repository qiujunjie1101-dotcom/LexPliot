# LexPilot

企业级合同审查 Agent —— 基于 FastAPI、LangGraph、PostgreSQL + pgvector 的 RAG 合同审查系统。

## 文档

- [系统设计规格](docs/superpowers/specs/2026-10-19-contract-review-agent-design.md)
- [Phase 0 中文计划](docs/superpowers/plans/2026-10-19-lexpilot-phase-0-foundation-zh.md)

## 当前状态

Phase 0 认证闭环已完成：

- FastAPI + PostgreSQL + Redis
- JWT 登录、Refresh Token 轮换、登出、`/me`
- RBAC + ACL、管理员用户管理、幂等创建
- Vue 3 登录页与工作台
- Alembic 初始迁移、测试与 Seed CLI

## 本地启动

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

另开终端启动前端：

```bash
cd frontend
npm install
npm run dev
```

访问：

- 前端：http://localhost:5175
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health/ready

开发账号：

```text
租户：acme
邮箱：admin@example.com
密码：Admin123!
```

> 本机 5173/5174 已被其他前端占用，因此 LexPilot 前端使用 5175。
> PostgreSQL 映射到宿主机 55432，Redis 映射到 56379，避免与已有服务冲突。

## 测试

```bash
cd backend
uv run ruff check .
uv run mypy app
uv run pytest

cd ../frontend
npm run lint
npm run test:unit
npm run build
```

## 设计边界

- LLM 不独立决定法律风险；风险结论由确定性 Rules Engine 产生（Phase 3 实现）。
- 人工复核等待期间不占用 Celery Worker（Phase 3 实现）。
- 不提供自由问答，不拆微服务。
