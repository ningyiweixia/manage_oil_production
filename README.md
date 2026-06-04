# 采油二厂井下作业管理系统

后端采用 `FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL 15(JSONB) + Redis + JWT + Alembic`。当前已完成：

- 模块 1：系统总体底层搭建
- 模块 2：上修项目池管理
- 模块 3：系统基础支撑与管理模块（RBAC + 统一身份认证）

## 项目结构

```text
manage_factory/
  app/
    api/
      deps.py
      v1/
        router.py
        endpoints/
          auth.py
          rbac.py
          workover_project_pools.py
    core/
      config.py
      exceptions.py
      middleware.py
      redis.py
      security.py
      status_codes.py
    crud/
      rbac.py
      workover_project_pool.py
    db/
      base.py
      seed.py
      session.py
    models/
      approval.py
      dictionary.py
      engineering.py
      rbac.py
      workover.py
    schemas/
      auth.py
      pagination.py
      rbac.py
      response.py
      workover_project_pool.py
    services/
      audit_service.py
      auth_service.py
      dictionary_service.py
      notification_service.py
      rbac_service.py
      workover_project_pool_excel.py
    utils/
      jsonb.py
  alembic/
    versions/
      20260531_0001_init_core_tables.py
      20260602_0002_workover_project_pool_module.py
      20260604_0003_system_support_rbac.py
  main.py
  requirements.txt
```

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
net start postgresql-x64-15
alembic upgrade head
python -m app.db.seed
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

访问入口：

- 健康检查：`GET http://127.0.0.1:8000/health`
- Swagger：`http://127.0.0.1:8000/docs`
- 登录：`POST /api/v1/auth/login`

初始化账号：

```json
{"username": "admin", "password": "ChangeMe_123!"}
```

## 环境配置

`.env.example` 是模板，实际运行使用 `.env`，不要提交 `.env`。

```env
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=manage_factory
REDIS_URL=redis://127.0.0.1:6379/0
JWT_SECRET_KEY=please-change-this-secret-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_MINUTES=10080
```

Redis 用于缓存用户权限列表。若本地 Redis 不可用，代码会自动降级为进程内缓存，保证开发环境可运行；生产部署按 `requirements.txt` 安装并配置 Redis。

## 统一接口规范

所有业务接口统一返回：

```json
{"code": 20000, "msg": "success", "data": {}}
```

业务码：

- `20000`：成功
- `40001`：参数错误
- `40100`：登录失效
- `40300`：越权访问
- `40900`：业务冲突

## 系统基础支撑与管理模块

模块范围：RBAC 权限体系 + 统一身份认证。

核心能力：

- 账号密码登录，签发 Access Token 与 Refresh Token。
- JWT 全局鉴权中间件。
- 路由级 RBAC 权限依赖。
- 登出与刷新令牌。
- Redis 缓存用户权限列表。
- 操作日志自动记录用户、IP、请求方法、路径、权限标识、业务返回码。
- 支持 CORS 白名单配置，适配 DMZ / APP / DB 分区部署。

标准 RBAC 表：

- `sys_user`：用户
- `sys_role`：角色
- `sys_user_role`：用户角色关联
- `sys_menu`：菜单/动态路由
- `sys_permission`：接口权限
- `sys_role_menu`：角色菜单关联
- `sys_role_permission`：角色接口权限关联
- `sys_operation_log`：操作日志

认证接口：

```text
POST /api/v1/auth/login    登录，返回用户信息、权限、菜单和令牌
POST /api/v1/auth/refresh  刷新 access token
POST /api/v1/auth/logout   登出并吊销 refresh token
GET  /api/v1/auth/me       当前用户信息
```

管理接口：

```text
GET    /api/v1/users
POST   /api/v1/users
PUT    /api/v1/users/{user_id}
PATCH  /api/v1/users/{user_id}/active
PATCH  /api/v1/users/{user_id}/roles
DELETE /api/v1/users/{user_id}

GET    /api/v1/roles
POST   /api/v1/roles
PUT    /api/v1/roles/{role_id}
PATCH  /api/v1/roles/{role_id}/menus
PATCH  /api/v1/roles/{role_id}/permissions
DELETE /api/v1/roles/{role_id}

GET    /api/v1/menus
POST   /api/v1/menus
PUT    /api/v1/menus/{menu_id}
DELETE /api/v1/menus/{menu_id}

GET    /api/v1/permissions
POST   /api/v1/permissions
PUT    /api/v1/permissions/{permission_id}
DELETE /api/v1/permissions/{permission_id}

GET    /api/v1/operation-logs
```

## 上修项目池管理模块

路由前缀：

```text
/api/v1/workover-project-pools/
```

已实现能力：

- 基层单位录入井号、井名、层位、故障描述、属地单位、区块、措施 JSON、备注。
- 项目池管理员维护台账，支持单条新增、详情、修改、逻辑删除。
- 多条件筛选分页：区块、井号、审批状态、措施类型。
- JSONB 原生检索：`measures_jsonb @>`，不把全量数据加载进 Pandas。
- 选井提报：`PATCH /submit`，状态自动变为 `PENDING_GEOLOGY_VERIFY`。
- 提报、编辑、删除自动写入 `approval_log`，保存操作人、IP、前后数据快照。
- 提报后预留 WebSocket 待办推送地质所用户。
- Excel 导入导出：基于 Pandas 批量解析/导出，预留 Celery 异步入口。

主要接口：

```text
GET    /api/v1/workover-project-pools/
GET    /api/v1/workover-project-pools/{id}
POST   /api/v1/workover-project-pools/
PUT    /api/v1/workover-project-pools/{id}
PATCH  /api/v1/workover-project-pools/submit
PATCH  /api/v1/workover-project-pools/{id}/status
DELETE /api/v1/workover-project-pools/{id}
POST   /api/v1/workover-project-pools/import
GET    /api/v1/workover-project-pools/export/all
```

`workover_project_pool.measures_jsonb` 使用 PostgreSQL JSONB，并建立 GIN 索引：

```sql
CREATE INDEX ix_workover_project_pool_measures_gin
ON workover_project_pool
USING gin (measures_jsonb);
```

措施类型、井区等业务选项不得硬编码，应由 `data_dictionary` 维表维护。

## Alembic

```powershell
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "message"
```

当前迁移：

- `20260531_0001`：核心底层表
- `20260602_0002`：上修项目池管理模块
- `20260604_0003`：系统基础支撑与 RBAC 模块

## 验证记录

已完成本地验证：

- `pip install -r requirements.txt`
- `python -m compileall app main.py alembic`
- `alembic upgrade head`
- `python -m app.db.seed`
- 登录、当前用户、刷新令牌、登出均返回 `20000`
- 用户列表、菜单树、项目池列表均返回 `20000`
- 操作日志已写入 `sys_operation_log`
- 当前 Alembic 版本：`20260604_0003`

## 安全说明

- `.env`、`.local/`、日志、虚拟环境、缓存文件已加入 `.gitignore`。
- 不使用裸 SQL 拼接业务查询。
- 禁止爬虫对接外部系统。
- 高危编辑/删除/提报写入审计日志。
- 生产部署建议通过 Nginx 暴露 DMZ 入口，FastAPI 运行于 APP 区，PostgreSQL/Redis 运行于 DB 区。

## Container Deployment

服务器容器化部署与监控体系已在 `deploy/` 下提供，包含 Docker Compose、DMZ Nginx、FastAPI/前端容器、PostgreSQL、Redis、MinIO、Prometheus、Grafana、Cadvisor、Node Exporter、一键启动脚本和部署说明。

```powershell
.\deploy\scripts\deploy.ps1
```

详细步骤、端口、三区域网络、安全规范与离线镜像准备见 `deploy/README.md`。

## Containerized Deployment and Monitoring

The server containerization and monitoring module is provided under `deploy/`.
It includes production Docker Compose orchestration, DMZ Nginx reverse proxy,
FastAPI backend image, Vue3 frontend image, PostgreSQL, Redis, MinIO,
Prometheus, Grafana, Cadvisor, Node Exporter, persistent volumes, health checks,
and one-click deployment scripts for enterprise intranet environments.

Start the complete stack:

```powershell
.\deploy\scripts\deploy.ps1
```

Main access points:

- Application entry: `https://localhost/`
- Backend health check: `https://localhost/health`
- Grafana monitoring: `https://localhost/grafana/`

Network zoning:

- DMZ zone: Nginx reverse proxy, HTTPS termination, security headers, request filtering.
- APP zone: FastAPI backend, Vue3 frontend runtime, Prometheus, Grafana.
- DB zone: PostgreSQL, Redis, MinIO data services.

Operational checks:

```powershell
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml ps
curl.exe -k --ipv4 https://localhost/health
```

See `deploy/README.md` for deployment steps, port mapping, offline image
preparation, security requirements, logging, data volumes, monitoring dashboards,
and three-zone server deployment guidance.
