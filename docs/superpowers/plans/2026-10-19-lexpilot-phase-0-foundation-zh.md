# LexPilot Phase 0 实施计划（中文导读）

- 对应英文计划：`docs/superpowers/plans/2026-10-19-lexpilot-phase-0-foundation.md`
- 设计规格：`docs/superpowers/specs/2026-10-19-contract-review-agent-design.md`
- 日期：2026-10-19
- 范围：Phase 0（基础架构、认证、租户/RBAC、管理员用户、前端登录、CI）
- 实施状态（2026-10-20）：Task 1 已完成；实际采用 `app/modules/auth` 模块化布局；本地 PostgreSQL/Redis 映射为 `55432`/`56379`（避免与宿主机已有服务冲突）。

> 代码块仍是 Python / TypeScript / YAML，属于通用实现语言；本导读用中文解释每个任务“做什么、改哪些文件、怎么验证、代码在英文计划哪一段”。

---

## 1. Phase 0 要交付什么

Phase 0 只做**可运行的基础纵向切片**：

- FastAPI 后端 + PostgreSQL + Redis 本地 Docker Compose
- 数据库模型与 Alembic 初始迁移
- JWT 登录、Refresh Token 轮换、登出、`/me`
- 多租户、三角色 RBAC + 资源级 ACL 基础
- 管理员创建/查看用户
- 登录限流、幂等创建
- Vue 3 登录页与工作台
- Playwright 登录 E2E
- GitHub Actions 三层 CI（后端 / 前端 / E2E）

**Phase 0 不做**：合同上传、PDF/DOCX 解析、OCR、知识库、LangGraph 审查、Celery、MinIO、人工复核、报告导出。这些从 Phase 1 开始，会另写独立计划。

---

## 2. 关键技术决策

| 决策 | 内容 |
|---|---|
| Python | 3.12，用 `uv` 管理依赖与虚拟环境 |
| 后端 | FastAPI + 同步 SQLAlchemy 2.0（Phase 0 降低异步复杂度） |
| 数据库 | PostgreSQL 16 + pgvector 镜像；初始迁移先创建 `vector` / `btree_gist` 扩展 |
| Redis | 登录失败限流（5 次 / 15 分钟）；本地宿主端口 `56379` 映射容器 `6379` |
| 本地 PostgreSQL | 宿主端口 `55432` 映射容器 `5432`，避免与已有本地 PostgreSQL 冲突 |
| 认证 | Access JWT 15 分钟；Refresh Token 7 天并轮换 |
| Token 存放 | Refresh Token 放 `HttpOnly` Cookie（`lexpilot_refresh`，路径 `/api/v1/auth`）；Access Token 只放前端内存 |
| JWT | HS256，支持 `kid` 密钥轮换 |
| 租户 | 用户全局唯一；通过 `role_bindings` 归属租户；所有查询按 `tenant_id` 过滤 |
| RBAC | 管理员 / 法务审查员 / 业务提交者 |
| ACL | `resource_acl` 表，支持按用户或角色授权/拒绝 |
| 幂等 | `POST /api/v1/admin/users` 支持 `Idempotency-Key`，记录保留 24 小时 |
| 前端 | Vue 3 + Vite + Tailwind v4 + shadcn-vue 风格本地组件 + Pinia + Vue Router |
| 测试 | pytest + fakeredis + 真实 PostgreSQL；Vitest；Playwright |
| CI | GitHub Actions：backend / frontend / e2e 三个 job |

---

## 3. 任务总览

| 任务 | 名称 | 产出 |
|---|---|---|
| 1 | 后端脚手架与基础设施 | 可启动的 FastAPI、健康检查、Docker Compose |
| 2 | 数据库模型与初始迁移 | 6 张表、Alembic、测试夹具 |
| 3 | 认证基础能力 | 密码哈希、JWT、Refresh Token 轮换 |
| 4 | 认证 API 与登录限流 | 登录/刷新/登出/`me`/切换租户 |
| 5 | RBAC/ACL、管理员用户、幂等、CLI | 权限服务、管理员用户 API、seed 命令 |
| 6 | 前端登录与工作台 | 登录页、工作台、Auth Store、路由守卫 |
| 7 | E2E 与 CI | Playwright 登录测试、GitHub Actions |
| 8 | 文档与验收 | README、全量验证、验收清单 |

---

## 4. 逐任务中文说明

### Task 1：后端脚手架与基础设施

**目标**：后端能启动，`/health/live` 可用，Docker Compose 能拉起 PostgreSQL 与 Redis。

**主要文件**
- 根目录：`.python-version`、`.gitignore`、`.env.example`、`docker-compose.yml`
- `docker/postgres/init/01-create-test-db.sql`：创建测试库 `lexpilot_test`
- `backend/pyproject.toml`：依赖、pytest、ruff、mypy 配置
- `backend/Dockerfile`
- `backend/app/main.py`：FastAPI 应用工厂、CORS、请求 ID 中间件
- `backend/app/core/config.py`：环境变量配置
- `backend/app/api/health.py`：健康检查
- `backend/tests/test_health.py`

**实现要点**
- 使用 `uv sync` 安装依赖；`uv lock` 生成 `uv.lock`。
- `/health/live` 返回 `{"status":"ok"}`。
- Docker Compose 包含 `postgres`（pgvector 镜像）、`redis`、`api`。
- `.env.example` 提供数据库、Redis、JWT、CORS 配置模板。
- `.gitignore` 排除 `.env`、缓存、node_modules 等。

**验证**
```bash
cd backend
uv sync
uv run pytest tests/test_health.py -v
cd ..
docker compose config >/dev/null
```

**英文计划位置**：Task 1（Step 1–8），完整代码在对应代码块。

**提交**：`chore: scaffold backend, config, health endpoints, docker infra`

---

### Task 2：数据库模型、初始迁移、测试夹具

**目标**：建立 Phase 0 所需 6 张表，并确保迁移可重复执行。

**表清单**
1. `tenants`：租户
2. `users`：全局用户
3. `role_bindings`：用户在某租户下的角色
4. `refresh_tokens`：Refresh Token 哈希、家族、轮换关系
5. `resource_acl`：资源级 ACL
6. `idempotency_keys`：幂等键与响应缓存

**关键约束**
- `tenants.slug` 唯一；`users.email` 唯一。
- `role_bindings` 唯一键 `(tenant_id, user_id, role)`。
- `refresh_tokens.token_hash` 唯一；`family_id` 用于重放检测。
- `resource_acl` 的 subject 必须是“用户”或“角色”二选一（CHECK）。
- 外键默认 `RESTRICT`；幂等表随租户 `CASCADE`。
- 初始迁移创建 `vector`、`btree_gist` 扩展，验证 pgvector 镜像可用。

**主要文件**
- `backend/app/db/base.py`、`session.py`
- `backend/app/db/models/*.py`
- `backend/alembic.ini`、`backend/alembic/env.py`、`backend/alembic/versions/0001_initial.py`
- `backend/tests/conftest.py`
- `backend/tests/integration/test_schema_constraints.py`

**验证**
```bash
docker compose up -d postgres redis
cd backend
uv run alembic upgrade head
uv run pytest tests/integration/test_schema_constraints.py -v
```

**英文计划位置**：Task 2（Step 1–6）。

**提交**：`feat: add phase 0 database models and initial migration`

---

### Task 3：认证基础能力

**目标**：实现密码哈希、JWT 签发/校验、Refresh Token 轮换与重放检测。

**主要文件**
- `backend/app/core/security.py`
- `backend/app/services/auth_service.py`
- `backend/tests/unit/test_security.py`
- `backend/tests/integration/test_refresh_tokens.py`

**实现要点**
- 密码使用 Argon2。
- Access Token：`sub`（用户）、`tid`（租户）、`roles`、`type=access`、`jti`、`iat`、`exp`；Header 带 `kid`。
- Refresh Token：随机串只返回给客户端，数据库只存 SHA-256 哈希。
- 轮换：旧 Token 标记 `revoked_at`，新 Token 同一 `family_id`。
- 如果已撤销的旧 Token 再次被使用 → 撤销整个家族，返回 401。
- `switch_tenant` 先验证成员关系，再撤销旧 Refresh Token，避免切换失败把用户踢下线。

**验证**
```bash
cd backend
uv run pytest tests/unit/test_security.py tests/integration/test_refresh_tokens.py -v
```

**英文计划位置**：Task 3（Step 1–7）。

**提交**：`feat: add password, jwt, and refresh token primitives`

---

### Task 4：认证 API、登录限流、当前用户依赖

**目标**：提供完整登录闭环。

**API**
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/switch-tenant`

**关键行为**
- 登录成功返回 Access Token，并通过 `Set-Cookie` 写入 `HttpOnly` Refresh Cookie。
- 登录失败计数：同一 IP + 邮箱 5 次失败后返回 429；成功登录清零。
- `/me` 从 JWT 取用户和租户，再从数据库读取当前角色；角色变更立即生效。
- `/health/ready` 检查数据库与 Redis。
- CORS 允许 `localhost:5173`、`localhost:4173`、`127.0.0.1:4173`。

**主要文件**
- `backend/app/core/actor.py`
- `backend/app/api/deps.py`
- `backend/app/services/rate_limit.py`
- `backend/app/schemas/auth.py`
- `backend/app/api/v1/auth.py`
- `backend/app/api/health.py`（替换为真实 readiness）
- `backend/app/main.py`
- `backend/tests/integration/test_auth_api.py`
- `backend/tests/conftest.py`（增加 Redis 替身、TestClient、租户/用户夹具）

**验证**
```bash
cd backend
uv run pytest tests/integration/test_auth_api.py -v
```

**英文计划位置**：Task 4（Step 1–6）。

**提交**：`feat: add jwt auth api with refresh rotation and login rate limiting`

---

### Task 5：RBAC + ACL、管理员用户、幂等、Seed CLI

**目标**：管理员可以在当前租户内创建/查看用户；权限服务支持角色 + ACL；创建用户支持幂等。

**API**
- `GET /api/v1/admin/users`（仅管理员）
- `POST /api/v1/admin/users`（仅管理员，支持 `Idempotency-Key`）

**实现要点**
- `PermissionService.authorize(actor, permission, resource)`：
  - 租户不匹配直接拒绝。
  - 管理员放行。
  - 如果资源存在 ACL，按 ACL 判断；否则按角色权限判断。
- 幂等：同一键 + 相同请求体返回原响应；同一键 + 不同请求体返回 409。
- 用户、角色绑定、幂等记录在同一事务提交。
- CLI：
  - `create-tenant`
  - `create-admin`
  - `seed-dev`（创建 `acme` 租户和 `admin@example.com / Admin123!`）

**主要文件**
- `backend/app/services/permission_service.py`
- `backend/app/services/idempotency.py`
- `backend/app/schemas/user.py`
- `backend/app/api/v1/admin_users.py`
- `backend/app/cli.py`
- `backend/tests/unit/test_permissions.py`
- `backend/tests/integration/test_admin_users.py`

**验证**
```bash
cd backend
uv run pytest tests/unit/test_permissions.py tests/integration/test_admin_users.py -v
```

**英文计划位置**：Task 5（Step 1–6）。

**提交**：`feat: add rbac/acl, admin user api, idempotency, and seed cli`

---

### Task 6：前端登录页、工作台、Auth Store、路由守卫

**目标**：浏览器中完成登录 → 工作台 → 退出。

**页面**
- `/login`：租户、邮箱、密码；错误提示；提交中禁用按钮。
- `/`：显示租户、用户邮箱、角色；退出登录按钮。
- 路由守卫：受保护页面先尝试 `/auth/refresh`；失败跳登录。

**状态管理**
- Access Token 只存在 Pinia 内存。
- 页面刷新后通过 Refresh Cookie 恢复会话。
- 登出调用后端清除 Cookie，并清空前端状态。

**主要文件**
- `frontend/package.json`、配置文件
- `frontend/src/lib/api.ts`、`cn.ts`
- `frontend/src/stores/auth.ts`
- `frontend/src/router.ts`
- `frontend/src/components/ui/*`（Button / Input / Label / Card）
- `frontend/src/pages/LoginPage.vue`、`DashboardPage.vue`
- `frontend/src/stores/auth.spec.ts`

**验证**
```bash
cd frontend
npm install
npm run test:unit
npm run lint
npm run build
```

**英文计划位置**：Task 6（Step 1–6）。

**提交**：`feat: add vue login, dashboard, auth store, and route guard`

---

### Task 7：Playwright 登录 E2E 与 GitHub Actions CI

**目标**：真实后端 + 真实前端跑通登录 E2E；CI 分三层执行。

**E2E**
- `scripts/e2e_backend.sh`：启动依赖、执行迁移、seed、启动 uvicorn。
- `frontend/playwright.config.ts`：同时启动后端与 Vite。
- `frontend/tests/e2e/login.spec.ts`：登录 `acme / admin@example.com / Admin123!`，断言工作台可见。

**CI**
- `backend` job：ruff、mypy、Alembic、pytest。
- `frontend` job：ESLint、Vitest、build。
- `e2e` job：Playwright + Chromium，运行登录流程。

**验证**
```bash
cd frontend
npm run test:e2e
```

**英文计划位置**：Task 7（Step 1–6），CI YAML 完整内容在 Step 4。

**提交**：`ci: add playwright login e2e and layered github actions pipeline`

---

### Task 8：README、全量验证、Phase 0 验收

**目标**：任何人按 README 可以启动、登录、跑测试；全部验收项通过。

**主要动作**
- 更新 README：前置条件、启动命令、seed 账号、测试命令、设计边界。
- 执行全量验证：
  - 后端：`ruff`、`mypy`、`alembic upgrade head`、`pytest`
  - 前端：`lint`、`test:unit`、`build`
  - E2E：`npm run test:e2e`
  - CI YAML 语法、Compose 配置

**英文计划位置**：Task 8（Step 1–3）。

**提交**：`docs: document phase 0 setup, run, and verification`

---

## 5. 数据库表关系（Phase 0）

```text
tenants 1──N role_bindings N──1 users
tenants 1──N refresh_tokens N──1 users
tenants 1──N resource_acl
tenants 1──N idempotency_keys
```

- `refresh_tokens.replaced_by_id` 自关联，记录轮换链。
- `role_bindings` 是用户与租户之间的成员关系。
- 业务表尚未建立；Phase 1 会增加合同、解析节点、知识库等表，并沿用 `(tenant_id, ...)` 隔离模式。

---

## 6. Phase 0 验收清单

- [ ] `docker compose up -d postgres redis` 正常
- [ ] `uv run alembic upgrade head` 成功
- [ ] `seed-dev` 创建 `acme` 租户与管理员
- [ ] 登录成功，`/api/v1/auth/me` 返回用户、租户、角色
- [ ] Refresh Token 轮换成功；旧 Token 重放触发家族撤销
- [ ] 5 次登录失败后返回 429
- [ ] 非管理员访问 `/api/v1/admin/users` 返回 403
- [ ] 跨租户访问被拒绝
- [ ] 管理员创建用户具备幂等性，不同请求体返回 409
- [ ] Vue 登录 → 工作台 → 退出正常
- [ ] Playwright 登录 E2E 通过
- [ ] CI 的 backend / frontend / e2e 三个 job 全绿
- [ ] 没有密钥进入仓库

---

## 7. 需要你重点确认的决策

1. **同步 SQLAlchemy**：Phase 0 用同步会话与同步路由，降低认证阶段复杂度；Phase 3 的 LangGraph 也用同步执行。若你希望一开始就全异步，请现在提出。
2. **Refresh Token 放 HttpOnly Cookie**：不落 localStorage，降低 XSS 风险；Access Token 只放内存。
3. **Phase 0 范围**：只做基础认证与前端登录，不引入 MinIO/Celery/合同功能；这些在 Phase 1 计划中。
4. **E2E 使用真实后端**：不是 mock，CI 会拉起 PostgreSQL/Redis + 迁移 + seed + uvicorn。
5. **计划拆分**：Phase 0 单独一份计划；后续按“合同与解析 → 知识库与检索 → LangGraph 审查 → 人工复核/报告 → 评测与上线”分别出计划。

---

## 8. 审阅建议

- 先看本导读第 1–3 节，确认范围和技术决策。
- 再看第 4 节每个任务的“目标 / 文件 / 验证”，确认没有遗漏。
- 代码细节在英文计划对应 Task 的代码块中；如果需要，我可以把某个任务的代码逐段翻成中文说明，或者把整份计划逐句翻译。
- 确认后告诉我执行方式（子代理驱动或当前会话执行），我再开始 Task 1。
