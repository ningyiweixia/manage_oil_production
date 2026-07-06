# 采油二厂井下作业管理系统

后端采用 `FastAPI` + `SQLAlchemy 2.0` + `Pydantic v2` + `PostgreSQL 15 (JSONB)` + `Redis 7.4` + `Celery 5.4` + `JWT` + `Alembic`。前端采用 `Vue 3.5` + `Element Plus 2.9` + `ECharts 5.5` + `TypeScript 5.7` + `Vite 8.0`。系统支持 PostgreSQL/Redis/MinIO/A5/FPM 的生产接入，也支持本地 SQLite、内存缓存和模拟外部系统的降级联调。

## 快速入口

| 场景 | 地址/命令 |
|------|-----------|
| 前端开发服务 | `http://127.0.0.1:5173` |
| 后端 API | `http://127.0.0.1:8000/api/v1` |
| Swagger 文档 | `http://127.0.0.1:8000/docs` |
| 健康检查 | `http://127.0.0.1:8000/health` |
| 前端构建 | `cd frontend && npm run build` |
| 后端测试 | `python -m pytest` |
| 后端语法检查 | `python -m compileall app alembic tests` |

默认管理员账号：

```json
{"username": "admin", "password": "ChangeMe_123!"}
```

> 首次登录后请立即修改默认密码，并在生产环境替换 `.env` 中的所有默认密钥。

## 模块总览

| 模块 | 状态 | 说明 |
|------|------|------|
| 系统底层搭建 | 已完成 | PostgreSQL JSONB 模型、Alembic 迁移、统一异常处理、操作日志中间件、Prometheus 指标暴露、本地降级运行 |
| 上修项目池管理 | 已完成 | 项目池 CRUD、复杂 JSONB 措施字段、审批状态机、驳回重提智能路由、删除归档、Excel 导入导出 |
| RBAC 与统一认证 | 已完成 | JWT 双令牌（access + refresh）、登出吊销、用户/角色/菜单/权限全 CRUD、用户物理删除保护、动态菜单与权限按钮守卫 |
| 前端业务界面 | 已完成 | Vue 3 + Element Plus 9 个视图、审批工作台、WebSocket 实时待办提醒 |
| 数据统计分析 | 已完成 | ECharts KPI 卡片、柱状图、饼图、热力图、趋势图、图表 PNG 导出、Pandas DSL 查询引擎 |
| 承包商调度 | 已完成 | 运力报备、修井运行表、审批入库自动建运行表、优先派工排序、Redis 分布式锁防重复派工、进度自动推进 |
| A5 系统集成 | 已完成 | Celery 定时同步（每 30 分钟）、手动触发、SSO 跳转令牌、RESTful 回调（HMAC 签名）、异常/特殊工序统计、运行表回写 |
| 工程设计管理 | 已完成 | 规则引擎（5 项校验）、python-docx/openpyxl 模板渲染、MinIO 归档、自动版本管理 |
| 物料管理与配送 | 已完成（V4新增） | 物料需求 CRUD、状态流转（待处理->已审核->已计划->已出库->已到场->已使用）、异常提醒、与修井运行表关联 |
| 完井分类台账 | 已完成（V4新增） | 按措施类型分类台账、修前/修后关键数据记录、完井日期/施工队伍管理、措施类型分组统计 |
| 项目池字段增强 | 已完成（V4新增） | 新增井别、县区、发起人、联系电话、照片附件等字段，完善业务数据采集 |
| 修井运行基础统计 | 已完成（V4新增） | 运行表总数、状态分布、派工完成率、完工率、队伍工作量排名、措施类型分布 |

## 项目结构

```text
manage_oil_production/
|-- main.py                        # FastAPI 应用入口
|-- celery_app.py                  # Celery 分布式任务队列配置
|-- requirements.txt               # Python 依赖
|-- alembic.ini                    # 数据库迁移配置
|-- docker-compose.yml             # 容器编排（11 服务）
|-- AGENTS.md                      # AI Agent 开发上下文文档
|-- STARTUP_LOG.md                 # 本地启动验证记录
|-- runtime-dashboard.html         # 运行时状态仪表盘
|
|-- alembic/                       # 数据库迁移
|   |-- versions/                  # 10 个迁移脚本
|
|-- app/                           # 后端应用
|   |-- api/
|   |   |-- deps.py                # 权限依赖注入（get_current_user / require_permission）
|   |   |-- ws.py                  # WebSocket 审批通知（ApprovalConnectionManager）
|   |   |-- v1/
|   |       |-- router.py          # API 路由聚合
|   |       |-- endpoints/
|   |           |-- auth.py        # 登录/刷新/登出/当前用户
|   |           |-- rbac.py        # 用户/角色/菜单/权限 CRUD + 操作日志/审批日志
|   |           |-- workover_project_pools.py  # 上修项目池（CRUD/提交/审批/Excel/分析）
|   |           |-- contractors.py # 承包商运力/修井运行表/派工/进度
|   |           |-- dictionaries.py# 数据字典 CRUD
|   |           |-- engineering.py # 工程设计文档（生成/下载/规则校验）
|   |           |-- a5_integration.py # A5 集成（回调/SSO/同步状态/手动触发）
|   |           |-- materials.py   # 物料管理与配送（V4新增）
|   |           |-- completions.py # 完井分类台账（V4新增）
|   |-- core/
|   |   |-- config.py              # 应用配置（Pydantic Settings，环境变量驱动）
|   |   |-- exceptions.py          # 全局异常处理（BusinessException + 多类处理器）
|   |   |-- middleware.py          # AuthMiddleware（JWT）+ OperationLogMiddleware（审计）
|   |   |-- redis.py               # Redis 缓存客户端（自动降级到内存字典）
|   |   |-- security.py            # JWT 签发/解码/吊销（pbkdf2_sha256 + jose）
|   |   |-- status_codes.py        # 业务状态码常量
|   |-- crud/
|   |   |-- rbac.py                # 用户/角色/菜单/权限 CRUD 查询
|   |   |-- workover_project_pool.py # 项目池 CRUD + 状态机
|   |   |-- contractor.py          # 承包商 CRUD + 修井运行表
|   |   |-- dictionary.py          # 数据字典 CRUD
|   |   |-- material.py            # 物料管理 CRUD（V4新增）
|   |   |-- completion.py          # 完井台账 CRUD（V4新增）
|   |-- db/
|   |   |-- base.py                # ORM 基类（TimestampMixin）+ 约束命名规范
|   |   |-- seed.py                # 种子数据
|   |   |-- session.py             # 数据库引擎/会话工厂 + SQLite JSONB 兼容
|   |-- models/
|   |   |-- rbac.py                # User/Role/Menu/Permission/OperationLog + 3 中间表
|   |   |-- workover.py            # WorkoverProjectPool/ContractorCapacity/WorkoverOperationSheet
|   |   |-- approval.py            # ApprovalLog（before/after JSONB 数据快照）
|   |   |-- dictionary.py          # DataDictionary
|   |   |-- engineering.py         # EngineeringDesignDoc
|   |   |-- material.py            # MaterialRequirement（V4新增：物料需求与配送）
|   |   |-- completion.py          # WellCompletionRecord（V4新增：完井分类台账）
|   |-- schemas/                   # Pydantic v2 请求/响应模型
|   |-- services/                  # 业务逻辑服务层（15 个服务文件）
|   |   |-- auth_service.py        # 认证流程
|   |   |-- rbac_service.py        # RBAC 业务逻辑
|   |   |-- workover_analytics_service.py  # Pandas DSL 统计分析引擎
|   |   |-- workover_project_pool_excel.py # Excel 导入导出
|   |   |-- dispatch_service.py    # Redis 分布式派工锁
|   |   |-- notification_service.py # WebSocket 审批待办推送
|   |   |-- engineering_design_service.py  # 工程设计文档生成流水线
|   |   |-- design_rule_engine.py  # 工程设计规则引擎（5 项校验）
|   |   |-- template_renderer.py   # 模板渲染 + MinIO 存储
|   |   |-- contractor_service.py  # 承包商状态管理
|   |   |-- audit_service.py       # 审批日志写入
|   |   |-- dictionary_service.py  # 字典值校验
|   |   |-- a5_client.py           # A5 系统 HTTP 客户端
|   |   |-- a5_auth_service.py     # A5 SSO 令牌生成 + 回调 HMAC 签名验证
|   |   |-- a5_sync_service.py     # A5 数据同步 + 告警触发
|   |   |-- a5_data_cleaner.py     # A5 数据清洗
|   |   |-- fpm_client.py          # 防偏磨系统 HTTP 客户端
|   |-- tasks/
|   |   |-- a5_tasks.py            # Celery 定时任务（每 30 分钟同步 A5）
|   |-- utils/
|       |-- jsonb.py               # JSONB 查询辅助工具
|
|-- frontend/                      # Vue 3 + TypeScript 前端
|   |-- src/
|       |-- api/                   # HTTP API 封装层（8 个模块文件）
|       |-- composables/           # Vue 组合式函数
|       |-- router/                # Vue Router 配置（14 路由 + JWT 守卫）
|       |-- styles/                # 全局样式
|       |-- types/                 # TypeScript 类型定义
|       |-- utils/                 # 工具函数
|       |-- views/                 # 9 个页面视图组件
|
|-- deploy/                        # 部署与基础设施
|   |-- docker/                    # 6 个 Dockerfile
|   |-- frontend-dist/             # 前端构建产物
|   |-- nginx/                     # Nginx 配置
|   |-- prometheus/                # Prometheus 配置 + 告警规则
|   |-- grafana/                   # Grafana 仪表板预配置
|   |-- scripts/                   # 一键部署脚本
|
|-- tests/                         # 后端测试
    |-- backend/
        |-- test_database_unavailable.py
        |-- test_a5_sync_service.py
```

## 本地开发

### 前置条件

- Python 3.12+
- Node.js 20+
- PostgreSQL 15（可选，无 PostgreSQL 时自动使用 SQLite）
- Redis（可选，无 Redis 时自动降级为内存缓存）

### 后端

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 数据库迁移（PostgreSQL 或 SQLite 均可）
alembic upgrade head
python -m app.db.seed

# 启动后端
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

访问入口：

- 健康检查：`GET http://127.0.0.1:8000/health`
- Swagger 文档：`http://127.0.0.1:8000/docs`
- Prometheus 指标：`http://127.0.0.1:8000/metrics`

### 前端

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

访问入口：

- 前端开发服务：`http://127.0.0.1:5173`
- 默认代理后端：`http://127.0.0.1:8000/api/v1`
- WebSocket 代理：`ws://127.0.0.1:8000/ws`

### 本地辅助脚本

仓库提供了 Windows PowerShell 辅助脚本：

```powershell
.\scripts\start-local-backend.ps1
.\scripts\check-local.ps1
.\scripts\visual-health.ps1
```

- `start-local-backend.ps1`：以本地环境变量启动后端服务
- `check-local.ps1`：检查后端健康、前端页面和关键代理链路
- `visual-health.ps1`：执行基础视觉健康检查

更详细的本地启动记录见 `STARTUP_LOG.md`。

### Celery 异步任务

```bash
# 启动 Celery Worker + Beat（定时任务）
celery -A celery_app worker --loglevel=info --beat
```

- 定时任务：`sync-a5-data-every-30min`（每 30 分钟拉取 A5 数据）
- 失败重试：最多 3 次，间隔 60 秒
- 连续失败 3 次触发企业微信告警

## 环境配置

复制 `.env.example` 为 `.env` 并根据本地环境修改：

```env
DEBUG=true
POSTGRES_SERVER=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=manage_factory
REDIS_URL=redis://127.0.0.1:6379/0
JWT_SECRET_KEY=<generate-a-random-secret>
ADMIN_INITIAL_PASSWORD=ChangeMe_123!
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_MINUTES=10080
AUTH_WHITELIST=/docs,/docs/oauth2-redirect,/redoc,/openapi.json,/health,/metrics,/api/v1/auth/login,/api/v1/auth/refresh,/api/v1/auth/logout,/api/v1/a5/callback
CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
A5_BASE_URL=
FPM_BASE_URL=
MINIO_ENDPOINT=127.0.0.1:9000
```

> `.env` 已加入 `.gitignore`，禁止提交。Redis 不可用时自动降级为进程内缓存；本地未配置 A5/FPM/MinIO 时，系统会使用空数据、模拟参数和 `local_minio/` 本地文件目录继续完成联调。

### 外部系统对接配置

```env
# A5 系统集成
A5_BASE_URL=           # A5 系统地址（空则使用模拟降级）
A5_API_KEY=            # A5 API 密钥
A5_API_SECRET=         # A5 API 密钥（HMAC 签名）
A5_IP_WHITELIST=       # IP 白名单
ALERT_WEBHOOK_URL=     # 企业微信告警 Webhook

# MinIO 对象存储
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_ENGINEERING=engineering-designs
MINIO_BUCKET_TEMPLATES=design-templates

# 防偏磨设计系统
FPM_BASE_URL=          # 防偏磨系统地址（空则使用模拟参数）
```

> 生产/联调环境接入真实系统时再填入 `A5_BASE_URL` 和 `FPM_BASE_URL`。A5 系统的回调路径 `/api/v1/a5/callback` 已在 `AUTH_WHITELIST` 中免鉴权，由 HMAC 签名验证保障安全。

### 本地降级模式

| 依赖 | 不可用时的行为 |
|------|---------------|
| PostgreSQL | 自动使用 SQLite（`local_dev.db`），JSONB -> JSON 兼容适配 |
| Redis | 缓存和分布式锁回退到进程内存实现 |
| MinIO | 工程设计文档写入 `local_minio/` 本地目录 |
| A5 系统 | 同步任务返回空数据并记录成功状态，前端正常展示 |
| FPM 系统 | 工程设计使用模拟防偏磨参数 |

## API 规范

### 统一响应格式

```json
{"code": 20000, "msg": "success", "data": {}}
```

### 业务状态码

| 状态码 | 含义 | HTTP |
|--------|------|------|
| `20000` | 成功 | 200 |
| `40001` | 参数错误 | 400 |
| `40100` | 登录失效 | 401 |
| `40300` | 越权访问 | 403 |
| `40900` | 业务冲突（并发冲突） | 409 |
| `42900` | 请求过于频繁 | 429 |
| `50300` | 数据库不可用 | 503 |
| `60001` | A5 系统联动失败 | 502 |
| `60002` | 防偏磨系统联动失败 | 502 |

### API 标准生命周期（6 步法）

`请求发起 -> 身份认证（AuthMiddleware）-> 参数校验（Pydantic v2）-> 事务执行 -> 操作留痕（OperationLogMiddleware + approval_log 快照）-> 结果返回`

## 认证与权限（RBAC）

### 认证接口

```text
POST /api/v1/auth/login      登录，返回用户信息、权限树、菜单树和双令牌
POST /api/v1/auth/refresh    刷新 access token
POST /api/v1/auth/logout     登出并吊销 refresh token（Redis JTI 黑名单）
GET  /api/v1/auth/me         当前用户信息
```

- JWT 双令牌：access_token（默认 120 分钟）+ refresh_token（默认 7 天）
- 登录限流：每 IP 每 5 分钟最多 5 次尝试
- 登出吊销：基于 JTI 的 Redis 黑名单机制

### RBAC 管理接口

```text
GET    /api/v1/users                   用户列表
POST   /api/v1/users                   新增用户
PUT    /api/v1/users/{user_id}         编辑用户
PATCH  /api/v1/users/{user_id}/active  启停用户
PATCH  /api/v1/users/{user_id}/roles   分配角色
DELETE /api/v1/users/{user_id}         删除用户（物理删除，超级管理员禁止删除）

GET    /api/v1/roles                   角色列表
POST   /api/v1/roles                   新增角色
PUT    /api/v1/roles/{role_id}         编辑角色
PATCH  /api/v1/roles/{role_id}/menus        分配菜单
PATCH  /api/v1/roles/{role_id}/permissions  分配权限
DELETE /api/v1/roles/{role_id}         删除角色

GET    /api/v1/menus                   菜单列表（树形，支持父子嵌套）
POST   /api/v1/menus                   新增菜单
PUT    /api/v1/menus/{menu_id}         编辑菜单
DELETE /api/v1/menus/{menu_id}         删除菜单

GET    /api/v1/permissions             权限列表
POST   /api/v1/permissions             新增权限
PUT    /api/v1/permissions/{perm_id}   编辑权限
DELETE /api/v1/permissions/{perm_id}   删除权限

GET    /api/v1/operation-logs          操作日志查询（分页）
GET    /api/v1/approval-logs           审批日志查询
```

### 内置角色

| 角色 | 编码 | 说明 |
|------|------|------|
| 超级管理员 | `super_admin` | 全部权限 |
| 项目池管理员 | `project_pool_admin` | 项目池 CRUD + 提交管理 |
| 基层录入员 | `base_entry_clerk` | 基层单位项目池数据录入 |
| 业务审核员 | `business_reviewer` | 地质/工艺审核 |
| 承包商操作员 | `contractor_operator` | 运力报备 |
| 运维管理员 | `ops_admin` | 系统监控 + A5 集成管理 |

## 上修项目池管理

### 审批状态机

```
DRAFT -> PENDING_GEOLOGY_VERIFY -> PENDING_PROCESS_VERIFY -> APPROVED -> DISPATCHED
                 |                        |
                 |-- REJECTED <-----------|
```

### 状态转换规则

| 当前状态 | 允许转换到 |
|----------|-----------|
| `DRAFT` | `PENDING_GEOLOGY_VERIFY` |
| `PENDING_GEOLOGY_VERIFY` | `PENDING_PROCESS_VERIFY`, `REJECTED` |
| `PENDING_PROCESS_VERIFY` | `APPROVED`, `REJECTED` |
| `APPROVED` | `DISPATCHED` |
| `REJECTED` | `DRAFT`, `PENDING_GEOLOGY_VERIFY`, `PENDING_PROCESS_VERIFY` |
| `DISPATCHED` | 无 |

### 驳回智能路由

从驳回状态重新提报时，系统自动从审批日志中查找驳回前的审批节点：

- 在地质核实被驳回 -> 重新提交至**地质核实**
- 在工艺核实被驳回 -> 重新提交至**工艺核实**

### 主要接口

```text
GET    /api/v1/workover-project-pools/                列表（分页、多条件筛选）
GET    /api/v1/workover-project-pools/{id}            详情
POST   /api/v1/workover-project-pools/                新增草稿
PUT    /api/v1/workover-project-pools/{id}            编辑
DELETE /api/v1/workover-project-pools/{id}            删除归档
PATCH  /api/v1/workover-project-pools/submit          批量提交至审批
PATCH  /api/v1/workover-project-pools/{id}/status     审批通过/驳回/重新提报
POST   /api/v1/workover-project-pools/import          Excel 导入
GET    /api/v1/workover-project-pools/export/all      Excel 导出
GET    /api/v1/workover-project-pools/analytics/summary  统计分析
```

## 承包商调度

### 智能派工排序

派工接口严格按以下规则排序：
1. 审批通过时间升序（先审批的优先派工）
2. 产量优先级降序（高优先级优先）

### Redis 分布式锁防重

```
PATCH /api/v1/contractors/dispatch
```

- 锁 KEY：`dispatch:lock:{contractor_capacity_id}`
- TTL：30 秒（防死锁）
- 加锁失败返回 `40900` 并发冲突

### 施工进度状态机

```
WAITING_DISPATCH -> DISPATCHED -> WORKING -> FINISHED
                        |            |
                        |-- CANCELED -|
```

### 修井运行基础统计

```text
GET /api/v1/contractors/analytics/summary
```

返回运行表总数、状态分布、派工完成率、完工率、队伍工作量排名、措施类型分布等统计信息。

## A5 系统集成

### 主要接口

```text
POST  /api/v1/a5/callback                 接收 A5 工单状态回调（HMAC 签名验证）
POST  /api/v1/a5/sso-token                生成 SSO 跳转令牌（JWT，5 分钟有效）
GET   /api/v1/a5/sync/status              查看最近一次同步状态
GET   /api/v1/a5/analytics/summary        查看 A5 异常和特殊工序统计
POST  /api/v1/a5/sync/trigger             手动触发全量数据同步
```

## 工程设计管理

### 文档生成流水线

```
获取项目信息 -> 调用防偏磨系统获取参数 -> 规则引擎校验（5 项）
-> 自动生成版本号 -> 模板渲染（python-docx / openpyxl）
-> MinIO 归档 -> 写入审计日志
```

### 主要接口

```text
GET    /api/v1/engineering-designs/                  工程设计文档列表（分页）
POST   /api/v1/engineering-designs/generate          一键生成工程设计文档
GET    /api/v1/engineering-designs/{id}              文档详情
GET    /api/v1/engineering-designs/{id}/download     获取 MinIO 预签名下载链接
DELETE /api/v1/engineering-designs/{id}              删除文档
POST   /api/v1/engineering-designs/check-rules       手动触发规则校验
```

## 物料管理与配送（V4新增）

```text
GET    /api/v1/materials/                物料需求列表（分页）
POST   /api/v1/materials/                创建物料需求
GET    /api/v1/materials/{req_id}        物料详情
PUT    /api/v1/materials/{req_id}        更新物料需求
DELETE /api/v1/materials/{req_id}        删除物料需求
GET    /api/v1/materials/analytics/summary  物料统计
```

物料状态流转：`待处理 -> 已审核 -> 已计划 -> 已出库 -> 已到场 -> 已使用`

## 完井分类台账（V4新增）

```text
GET    /api/v1/well-completions/          完井记录列表（分页）
POST   /api/v1/well-completions/          创建完井记录
GET    /api/v1/well-completions/{id}      记录详情
PUT    /api/v1/well-completions/{id}      更新记录
DELETE /api/v1/well-completions/{id}      删除记录
GET    /api/v1/well-completions/analytics/summary  按措施类型统计
```

## 数据库迁移

```bash
alembic upgrade head           # 升级到最新
alembic downgrade -1           # 回退一个版本
alembic revision --autogenerate -m "描述"
```

### 迁移历史

| 版本 | 日期 | 内容 |
|------|------|------|
| `20260531_0001` | 2026-05-31 | 核心底层表 + RBAC 体系 |
| `20260602_0002` | 2026-06-02 | 上修项目池模块 + data_dictionary |
| `20260604_0003` | 2026-06-04 | 系统基础支撑与 RBAC 完善 |
| `20260616_0004` | 2026-06-16 | 安全与数据完整性修复 |
| `20260629_0005` | 2026-06-29 | 支持用户物理删除 |
| `150795c9dad6` | 2026-06-30 | 移除项目池 VOIDED 状态 |
| `20260630_0006` | 2026-06-30 | 修井运行表新增 A5 同步字段 |
| `20260705_0007` | 2026-07-05 | 项目池字段增强（井别/县区/发起人/照片） |
| `20260705_0008` | 2026-07-05 | 创建物料需求表 |
| `20260705_0009` | 2026-07-05 | 创建完井分类台账表 |
| `20260705_0010` | 2026-07-05 | 添加外键索引和字典约束 |

## 安全说明

- `.env`、`.local/`、日志、虚拟环境、缓存文件已加入 `.gitignore`
- 所有查询使用参数化，禁止裸 SQL 拼接
- 高危操作自动写入 `approval_log` 审计日志，含变更前后 JSONB 数据快照
- JWT 全局鉴权（AuthMiddleware）+ 路由级 RBAC 权限校验（`require_permission`）
- Redis JTI 黑名单实现令牌吊销
- 登录接口内存滑动窗口限流（每 IP 每 5 分钟 5 次）
- A5 回调接口 HMAC 签名验证
- 生产环境 CSP 由 Nginx 注入
## 试运行验收与运维脚本

本地演示默认账号仍为 `admin / ChangeMe_123!`。后端和前端启动后，可执行以下命令做验收检查：

```powershell
.\scripts\acceptance-check.ps1
```

脚本会检查 `/health`、登录、项目池、审批日志、运行表、物料、完井、综合报表、操作日志以及 Excel/Word 报表导出。

本地 SQLite 演示库可用以下命令备份和恢复：

```powershell
.\scripts\backup-local-db.ps1
.\scripts\restore-local-db.ps1 -BackupPath .\backups\local_dev-YYYYMMDD-HHMMSS.db
```
