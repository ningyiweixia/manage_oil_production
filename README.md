# 采油二厂井下作业管理系统

后端采用 `FastAPI` + `SQLAlchemy 2.0` + `Pydantic v2` + `PostgreSQL 15 (JSONB)` + `Redis 7.4` + `Celery 5.4` + `JWT` + `Alembic`。前端采用 `Vue 3.5` + `Element Plus 2.9` + `ECharts 5.5` + `TypeScript 5.7` + `Vite 8.0`。当前核心模块全部实现，已完成本机联调巡检。

## 模块总览

| 模块 | 状态 | 说明 |
|------|------|------|
| 系统底层搭建 | ✅ 已完成 | PostgreSQL JSONB 模型、Alembic 迁移、统一异常处理、操作日志中间件、Prometheus 指标暴露 |
| 上修项目池管理 | ✅ 已完成 | 项目池 CRUD、复杂 JSONB 措施字段、审批状态机、驳回重提智能路由、Excel 导入导出 |
| RBAC 与统一认证 | ✅ 已完成 | JWT 双令牌（access + refresh）、登出吊销、用户/角色/菜单/权限全 CRUD、动态菜单与权限按钮守卫 |
| 前端业务界面 | ✅ 已完成 | Vue 3 + Element Plus 9 个视图、审批工作台、WebSocket 实时待办提醒 |
| 数据统计分析 | ✅ 已完成 | ECharts KPI 卡片、柱状图、饼图、热力图、趋势图、图表 PNG 导出、Pandas DSL 查询引擎 |
| 承包商调度 | ✅ 已完成 | 运力报备、修井运行表、优先派工排序、Redis 分布式锁防重复派工、进度自动推进 |
| A5 系统集成 | ✅ 已完成 | Celery 定时同步（每 30 分钟）、手动触发、SSO 跳转令牌、RESTful 回调（HMAC 签名）、同步状态跟踪 |
| 工程设计管理 | ✅ 已完成 | 规则引擎（5 项校验）、python-docx/openpyxl 模板渲染、MinIO 归档、自动版本管理 |

## 项目结构

```text
manage_oil_production/
├── main.py                          # FastAPI 应用入口
├── celery_app.py                    # Celery 分布式任务队列配置
├── requirements.txt                 # Python 依赖
├── alembic.ini                      # 数据库迁移配置
├── docker-compose.yml               # 容器编排（11 服务）
├── agent.md                         # AI Agent 开发上下文文档
├── runtime-dashboard.html           # 运行时状态仪表盘
│
├── alembic/                         # 数据库迁移
│   └── versions/                    # 4 个迁移脚本
│
├── app/                             # 后端应用
│   ├── api/
│   │   ├── deps.py                  # 权限依赖注入（get_current_user / require_permission）
│   │   ├── ws.py                    # WebSocket 审批通知（ApprovalConnectionManager）
│   │   └── v1/
│   │       ├── router.py            # API 路由聚合
│   │       └── endpoints/
│   │           ├── auth.py          # 登录/刷新/登出/当前用户
│   │           ├── rbac.py          # 用户/角色/菜单/权限 CRUD + 操作日志
│   │           ├── workover_project_pools.py  # 上修项目池（CRUD/提交/审批/Excel/分析）
│   │           ├── contractors.py   # 承包商运力/修井运行表/派工/进度
│   │           ├── dictionaries.py  # 数据字典 CRUD
│   │           ├── engineering.py   # 工程设计文档（生成/下载/规则校验）
│   │           └── a5_integration.py # A5 集成（回调/SSO/同步状态/手动触发）
│   ├── core/
│   │   ├── config.py                # 应用配置（Pydantic Settings，环境变量驱动）
│   │   ├── exceptions.py            # 全局异常处理（BusinessException + 6 类处理器）
│   │   ├── middleware.py            # AuthMiddleware（JWT）+ OperationLogMiddleware（审计）
│   │   ├── redis.py                 # Redis 缓存客户端（自动降级到内存字典）
│   │   ├── security.py              # JWT 签发/解码/吊销（pbkdf2_sha256 + jose）
│   │   └── status_codes.py          # 业务状态码常量（20000/40001/40100/40300/40900/50300/60001/60002）
│   ├── crud/
│   │   ├── rbac.py                  # 用户/角色/菜单/权限 CRUD 查询
│   │   ├── workover_project_pool.py # 项目池 CRUD + 状态机 + ALLOWED_STATUS_TRANSITIONS
│   │   ├── contractor.py            # 承包商 CRUD + 修井运行表
│   │   └── dictionary.py            # 数据字典 CRUD
│   ├── db/
│   │   ├── base.py                  # ORM 基类（TimestampMixin）+ 约束命名规范
│   │   ├── seed.py                  # 种子数据（17 菜单/46 权限/6 角色/15 字典/1 管理员）
│   │   └── session.py               # 数据库引擎/会话工厂 + SQLite JSONB 兼容
│   ├── models/
│   │   ├── rbac.py                  # User/Role/Menu/Permission/OperationLog + 3 中间表
│   │   ├── workover.py              # WorkoverProjectPool/ContractorCapacity/WorkoverOperationSheet
│   │   ├── approval.py              # ApprovalLog（before/after JSONB 数据快照）
│   │   ├── dictionary.py            # DataDictionary
│   │   └── engineering.py           # EngineeringDesignDoc
│   ├── schemas/                     # Pydantic v2 请求/响应模型（auth/rbac/workover/contractor/...)
│   ├── services/                    # 业务逻辑服务层（15 个服务文件）
│   │   ├── auth_service.py          # 认证流程（登录/令牌刷新/权限缓存/角色构建）
│   │   ├── rbac_service.py          # RBAC 业务逻辑
│   │   ├── workover_analytics_service.py  # Pandas DSL 统计分析引擎
│   │   ├── workover_project_pool_excel.py # Excel 导入导出（pandas + openpyxl）
│   │   ├── dispatch_service.py      # Redis 分布式派工锁
│   │   ├── notification_service.py  # WebSocket 审批待办推送
│   │   ├── engineering_design_service.py  # 工程设计文档生成流水线
│   │   ├── design_rule_engine.py    # 工程设计规则引擎（5 项校验）
│   │   ├── template_renderer.py     # 模板渲染（python-docx/openpyxl）+ MinIO 存储
│   │   ├── contractor_service.py    # 承包商状态管理
│   │   ├── audit_service.py         # 审批日志写入
│   │   ├── dictionary_service.py    # 字典值校验
│   │   ├── a5_client.py             # A5 系统 HTTP 客户端（httpx + 超时/重试）
│   │   ├── a5_auth_service.py       # A5 SSO 令牌生成 + 回调 HMAC 签名验证
│   │   ├── a5_sync_service.py       # A5 数据同步（日报/异常/工序）+ 告警触发
│   │   ├── a5_data_cleaner.py       # A5 数据清洗（Pandas 去重/格式化/填充）
│   │   └── fpm_client.py            # 防偏磨系统 HTTP 客户端（含模拟模式）
│   ├── tasks/
│   │   └── a5_tasks.py              # Celery 定时任务（每 30 分钟同步 A5）
│   └── utils/
│       └── jsonb.py                 # JSONB 查询辅助工具
│
├── frontend/                        # Vue 3 + TypeScript 前端
│   └── src/
│       ├── api/
│       │   ├── http.ts              # Axios 实例（Bearer Token 拦截 + 401 重定向 + unwrap）
│       │   ├── auth.ts              # 认证接口
│       │   ├── workover.ts          # 项目池/审批接口（含演示模式降级）
│       │   ├── contractor.ts        # 承包商调度接口
│       │   ├── engineering.ts       # 工程设计接口
│       │   ├── dictionary.ts        # 数据字典接口
│       │   ├── rbac.ts              # RBAC 管理接口
│       │   └── a5.ts                # A5 集成接口
│       ├── composables/
│       │   ├── useApprovalSocket.ts # WebSocket 管理（指数退避重连 + auth handshake）
│       │   └── useProjectSync.ts    # 跨组件事件总线
│       ├── router/
│       │   └── index.ts             # 14 路由 + JWT 导航守卫
│       ├── styles/
│       │   └── main.css             # 全局样式
│       ├── types/
│       │   └── workover.ts          # TypeScript 类型定义
│       ├── utils/
│       │   └── status.ts            # 审批状态/流转/标签工具函数
│       └── views/
│           ├── LoginView.vue        # 登录页
│           ├── MainLayout.vue       # 主布局（动态 RBAC 侧边栏 + 通知铃铛）
│           ├── ApprovalWorkbench.vue # 审批工作台（搜索/CRUD/批量提交/审批/WebSocket）
│           ├── AnalyticsDashboard.vue # 统计分析大屏（KPI/图表/热力图/趋势/导出）
│           ├── ContractorDispatchView.vue # 承包商运力与智能派工
│           ├── EngineeringDesignView.vue  # 工程设计管理
│           ├── A5IntegrationView.vue # A5 系统集成
│           ├── SystemAdminView.vue   # 系统管理（用户/角色/菜单/权限/日志 Tab）
│           └── DictionaryManageView.vue # 数据字典管理
│
├── deploy/                          # 部署与基础设施
│   ├── docker/                      # 6 个 Dockerfile（多阶段构建）
│   ├── frontend-dist/               # 前端构建产物
│   ├── nginx/                       # Nginx 配置（DMZ + SSL + 限流 + 安全头）
│   ├── prometheus/                  # Prometheus 配置 + 告警规则
│   ├── grafana/                     # Grafana 仪表板预配置
│   └── scripts/
│       ├── deploy.sh                # Linux 一键部署脚本
│       └── deploy.ps1               # Windows 一键部署脚本
│
└── tests/
    └── backend/
        └── test_database_unavailable.py  # 数据库不可用降级测试
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

### Celery 异步任务

```bash
# 启动 Celery Worker + Beat（定时任务）
celery -A celery_app worker --loglevel=info --beat
```

- 定时任务：`sync-a5-data-every-30min`（每 30 分钟拉取 A5 数据）
- 失败重试：最多 3 次，间隔 60 秒
- 连续失败 3 次触发企业微信告警

### 初始账号

```json
{"username": "admin", "password": "ChangeMe_123!"}
```

> ⚠️ 首次登录后请立即修改密码。

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
| PostgreSQL | 自动使用 SQLite（`local_dev.db`），JSONB → JSON 兼容适配 |
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
| `50300` | 数据库不可用 | 503 |
| `60001` | A5 系统联动失败 | 502 |
| `60002` | 防偏磨系统联动失败 | 502 |

### API 标准生命周期（6 步法）

`请求发起 → 身份认证（AuthMiddleware）→ 参数校验（Pydantic v2）→ 事务执行 → 操作留痕（OperationLogMiddleware + approval_log 快照）→ 结果返回`

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
DELETE /api/v1/users/{user_id}         删除用户（软删除）

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

GET    /api/v1/operation-logs          操作日志查询
```

### 内置角色（Seed Data）

| 角色 | 编码 | 说明 |
|------|------|------|
| 超级管理员 | `super_admin` | 全部权限 |
| 项目池管理员 | `pool_admin` | 项目池 CRUD + 提交管理 |
| 业务审核员 | `business_reviewer` | 地质/工艺审核 |
| 承包商操作人员 | `contractor_operator` | 运力报备 |
| 运维管理员 | `ops_admin` | 系统监控 + A5 集成管理 |
| 普通用户 | `viewer` | 只读查看 |

### 数据字典

```text
GET    /api/v1/dictionaries/               字典列表（支持 dict_type 筛选）
POST   /api/v1/dictionaries/               新增字典项
PUT    /api/v1/dictionaries/{id}           编辑字典项
PATCH  /api/v1/dictionaries/{id}/active    启停字典项
```

字典表维护措施类型、施工工序、井况分类等业务枚举，接口层通过 `ensure_dictionary_values` 强制校验。

## 上修项目池管理

### 审批状态机

```
DRAFT → PENDING_GEOLOGY_VERIFY → PENDING_PROCESS_VERIFY → APPROVED → DISPATCHED
  │              │                        │                    │
  └── VOIDED     └── REJECTED ←───────────┘                    └── VOIDED
                       │
                       └── VOIDED（作废）
```

### 状态转换规则

| 当前状态 | 允许转换到 |
|----------|-----------|
| `DRAFT` | `PENDING_GEOLOGY_VERIFY`, `VOIDED` |
| `PENDING_GEOLOGY_VERIFY` | `PENDING_PROCESS_VERIFY`, `REJECTED` |
| `PENDING_PROCESS_VERIFY` | `APPROVED`, `REJECTED` |
| `APPROVED` | `DISPATCHED`, `VOIDED` |
| `REJECTED` | `DRAFT`, `PENDING_GEOLOGY_VERIFY`, `PENDING_PROCESS_VERIFY`, `VOIDED` |

### 驳回智能路由

从驳回状态重新提报时，系统自动从审批日志中查找驳回前的审批节点：

- 在地质核实被驳回 → 重新提交至**地质核实**
- 在工艺核实被驳回 → 重新提交至**工艺核实**

### 主要接口

```text
GET    /api/v1/workover-project-pools/                列表（分页、多条件筛选）
GET    /api/v1/workover-project-pools/{id}            详情
POST   /api/v1/workover-project-pools/                新增草稿
PUT    /api/v1/workover-project-pools/{id}            编辑
DELETE /api/v1/workover-project-pools/{id}            软删除（标记作废）
PATCH  /api/v1/workover-project-pools/submit          批量提交至审批
PATCH  /api/v1/workover-project-pools/{id}/status     审批通过/驳回/重新提报
POST   /api/v1/workover-project-pools/import          Excel 导入（Pandas 批量解析）
GET    /api/v1/workover-project-pools/export/all      Excel 导出（base64）
GET    /api/v1/workover-project-pools/analytics/summary  统计分析聚合
```

### 筛选参数

| 参数 | 说明 |
|------|------|
| `page` / `page_size` | 分页 |
| `status` | 审批状态 |
| `well_no` | 井号（模糊匹配） |
| `block_name` | 区块（模糊匹配） |
| `measure_type` | 措施类型（字典值精确匹配） |

项目列表返回 `rejected_from_status` 字段，标明驳回项目在被驳回前所处的审批节点，前端据此区分「地质驳回」与「工艺驳回」。

## 承包商调度

### 智能派工排序

派工接口严格按以下规则排序（方案强制要求）：
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
WAITING_DISPATCH → DISPATCHED → WORKING → FINISHED
                        │            │
                        └── CANCELED ←┘
```

进度到达 100% 时自动推进：
- `DISPATCHED` → `WORKING`（`actual_start_at` 自动填入）
- `WORKING` → `FINISHED`（`actual_end_at` 自动填入）

### 主要接口

```text
GET    /api/v1/contractors/                               承包商运力列表（分页）
POST   /api/v1/contractors/                               新增运力报备（含 capability_tags）
GET    /api/v1/contractors/{id}                           运力详情
PUT    /api/v1/contractors/{id}                           更新运力报备

GET    /api/v1/contractors/priority-sheets                待派工优先顺序列表
GET    /api/v1/contractors/operation-sheets/              修井运行表列表（分页）
POST   /api/v1/contractors/operation-sheets/              创建修井运行表
GET    /api/v1/contractors/operation-sheets/{id}          运行表详情
PATCH  /api/v1/contractors/dispatch                       派工（Redis 分布式锁）
PATCH  /api/v1/contractors/operation-sheets/{id}/progress 更新施工进度
```

## A5 系统集成

### 集成架构

```
┌──────────┐  SSO 跳转（主动）   ┌──────────┐
│  本系统   │ ─────────────────→ │ A5 系统   │
│          │ ←─── 回调（被动）── │          │
│  Celery  │ ─── 定时拉取（主动）→ │          │
└──────────┘                    └──────────┘
```

### API 约束

- 所有集成接口使用 HTTPS + Token 身份双重鉴权
- 回调接口 `/api/v1/a5/callback` 加入 `AUTH_WHITELIST` 免 JWT 鉴权，由 HMAC 签名验证
- 配置 IP 白名单访问限制
- 全量接口调用自动落地日志

### 主要接口

```text
POST  /api/v1/a5/callback                 接收 A5 工单状态回调（HMAC 签名验证）
POST  /api/v1/a5/sso-token                生成 SSO 跳转令牌（JWT，5 分钟有效）
GET   /api/v1/a5/sync/status              查看最近一次同步状态（成功/失败/进行中/无记录）
POST  /api/v1/a5/sync/trigger             手动触发全量数据同步
```

### Celery 定时任务

- `sync-a5-data-every-30min`：每 30 分钟轮询拉取 A5 系统数据
- 拉取内容：作业日报、施工异常、工序进度
- 数据清洗：基于 Pandas 去重、日期格式化、缺失值填充
- 失败重试：最多 3 次，连续 3 次失败触发企业微信 Webhook 告警

### SSO 跳转流程

```text
前端点击"跳转A5" → POST /api/v1/a5/sso-token → 后端签发 JWT 临时令牌
→ 返回 redirect_url（含 token + well_no） → 前端跳转 A5 系统
→ A5 验证令牌后展示工单操作页面
```

## 工程设计管理

### 文档生成流水线

```
获取项目信息 → 调用防偏磨系统获取参数 → 规则引擎校验（5 项）
→ 自动生成版本号 → 模板渲染（python-docx / openpyxl）
→ MinIO 归档 → 写入审计日志
```

### 规则引擎校验项

| 规则 | 说明 |
|------|------|
| 抽油机型号匹配 | 井深 > 3000m 必须使用特定型号抽油机 |
| 措施冲突检测 | 酸化和冲砂洗井不能同工序进行 |
| 施工参数范围 | 压力 0–100MPa，温度 -50–500°C |
| 防偏磨参数完整性 | 必须包含 `casing_diameter`、`tubing_size`、`wear_level` |
| 防偏磨严重程度 | `wear_level=SEVERE` 时阻断生成 |

### 文档版本管理

- 版本号格式：`v1`, `v2`, `v3` … 自动递增
- 数据库 `UniqueConstraint(well_no, version)` 保证版本唯一

### 主要接口

```text
GET    /api/v1/engineering-designs/                  工程设计文档列表（分页）
POST   /api/v1/engineering-designs/generate          一键生成工程设计文档
GET    /api/v1/engineering-designs/{id}              文档详情
GET    /api/v1/engineering-designs/{id}/download     获取 MinIO 预签名下载链接
DELETE /api/v1/engineering-designs/{id}              删除文档
POST   /api/v1/engineering-designs/check-rules       手动触发规则校验
```

## 前端功能

### 审批工作台

- 项目池列表：多条件筛选、分页、优先级进度条、措施标签、审批流步骤条
- 批量提交：勾选草稿项目，一键提交至地质核实
- 审批操作：通过（流转到下一节点）、驳回（退回修改）
- 重新提报：根据 `rejected_from_status` 智能路由到地质核实或工艺核实
- 措施 JSONB 表单：动态增删措施行，措施类型下拉从字典 API 加载
- WebSocket 实时待办：页面加载后自动连接 `/ws/approval`，收到推送时弹窗提醒

### 统计分析大屏

- KPI 卡片：项目总数、待审批数、审批通过率、预计总费用、平均优先级
- 审批状态柱状图
- 措施类型饼图
- 区块 × 状态热力图
- 日提报趋势折线/柱状混合图
- 图表一键导出 PNG + 数据摘要文本导出

### RBAC 菜单集成

- 登录时获取用户菜单树（`menus`）和权限列表（`permissions`）
- 侧边栏菜单由后端 RBAC 数据动态驱动，支持父子嵌套、图标映射、不可见菜单过滤
- 操作按钮根据用户权限自动显示/隐藏
- 当后端 RBAC 数据不可用时，自动回退为静态菜单

### 权限按钮映射

| 按钮 | 所需权限 |
|------|----------|
| 新增提报 | `workover_project_pool:create` |
| 编辑项目 | `workover_project_pool:update` |
| 批量提交 | `workover_project_pool:submit` |
| 通过 / 驳回 | `workover_project_pool:approve` |
| 删除项目 | `workover_project_pool:delete` |

### WebSocket 消息格式

```json
{
  "title": "审批待办提醒",
  "message": "CY2-136 已提交至地质核实",
  "node_code": "PENDING_GEOLOGY_VERIFY",
  "type": "info"
}
```

连接管理：指数退避自动重连（最多 6 次），auth handshake 协议。

## Alembic 数据库迁移

```bash
alembic upgrade head           # 升级到最新
alembic downgrade -1           # 回退一个版本
alembic revision --autogenerate -m "描述"
```

### 迁移历史

| 版本 | 日期 | 内容 |
|------|------|------|
| `20260531_0001` | 2026-05-31 | 核心底层表 + RBAC 体系 |
| `20260602_0002` | 2026-06-02 | 上修项目池模块 + data_dictionary + 字段重命名 + 索引 |
| `20260604_0003` | 2026-06-04 | 系统基础支撑与 RBAC + sys_menu + sys_operation_log + 字段扩展 |
| `20260616_0004` | 2026-06-16 | 安全与数据完整性修复（进度 0-100 约束 + 索引 + action 枚举扩展） |

## 容器化部署

完整 Docker Compose 编排（11 服务，4 隔离网络）：

```bash
# 一键部署
# Linux
bash deploy/scripts/deploy.sh

# Windows
.\deploy\scripts\deploy.ps1
```

### 服务清单

| 服务 | 端口 | 网络区域 |
|------|------|----------|
| Nginx (DMZ) | 443 | dmz_net |
| Frontend (SPA) | — | app_net |
| Backend (FastAPI) | 8000 | app_net + db_net |
| PostgreSQL 15 | 5432 | db_net |
| Redis 7.4 | 6379 | db_net |
| MinIO | 9000/9001 | db_net |
| Prometheus | — | monitor_net |
| Grafana | — | monitor_net |
| cAdvisor | — | monitor_net |
| Node Exporter | — | monitor_net |

### 网络分区

```
dmz_net (前端接入域)  →  Nginx（HTTPS 终结 + HSTS + CSP + 限流 20 req/s + burst 40）
app_net (应用逻辑域)  →  FastAPI + Vue3 前端 + Prometheus + Grafana + cAdvisor + Node Exporter
db_net  (核心数据域)  →  PostgreSQL + Redis + MinIO（严禁外部直接访问）
monitor_net (监控域)  →  Prometheus + Grafana + 指标采集
```

### 访问入口

| 入口 | 地址 |
|------|------|
| 应用首页 | `https://localhost/` |
| 后端健康检查 | `https://localhost/health` |
| Grafana 监控 | `https://localhost/grafana/` |
| Prometheus | `https://localhost/prometheus/` |

### 监控告警规则

| 告警 | 条件 |
|------|------|
| 后端宕机 | 持续 2 分钟无响应 |
| API 高延迟 | p95 > 1s 持续 5 分钟 |
| 磁盘空间不足 | 可用空间 < 15% |
| 容器 CPU 过高 | 持续 5 分钟 > 80% |

详见 `deploy/README.md`。

## 安全说明

- `.env`、`.local/`、日志、虚拟环境、缓存文件已加入 `.gitignore`
- 所有查询使用参数化，禁止裸 SQL 拼接
- 高危操作（编辑/删除/提报/审批/派工/生成文档）自动写入 `approval_log` 审计日志，含变更前后 JSONB 数据快照
- JWT 全局鉴权（AuthMiddleware）+ 路由级 RBAC 权限校验（`require_permission` 依赖注入）
- Redis JTI 黑名单实现令牌吊销（主动登出即时失效）
- 登录接口内存滑动窗口限流（每 IP 每 5 分钟 5 次）
- 操作日志记录用户、IP、方法、路径、权限标识、返回码
- A5 回调接口 HMAC 签名验证
- 生产环境 CSP 由 Nginx 注入（HSTS + X-Frame-Options + XSS-Protection）
- 禁止提交 `frontend/src/**/*.js` / `*.js.map`（已加入 `.gitignore`）

## 验证记录

最近一次完整本机巡检：**2026-06-27**

- ✅ `pip install -r requirements.txt`
- ✅ `alembic upgrade head`
- ✅ `python -m app.db.seed`
- ✅ 登录 / 刷新 / 登出 / 当前用户
- ✅ 用户 / 角色 / 菜单 / 权限 CRUD + 操作日志
- ✅ 数据字典 CRUD
- ✅ 项目池 CRUD + 提交 + 审批 + 驳回 + 重新提报
- ✅ 智能路由（地质驳回 → 地质重提，工艺驳回 → 工艺重提）
- ✅ 操作日志自动写入（含 before/after JSONB 快照）
- ✅ WebSocket 审批待办推送（含 auth handshake + 指数退避重连）
- ✅ Excel 导入导出（Pandas 解析 + 公式消毒）
- ✅ 统计分析 API（Pandas DSL 引擎）
- ✅ `npm install && npm run build`
- ✅ `vue-tsc --noEmit` TypeScript 类型检查零错误
- ✅ Vue 3 前端构建产物输出到 `deploy/frontend-dist/`
- ✅ RBAC 菜单动态渲染 + 权限按钮守卫
- ✅ 驳回重提智能路由（前端使用 `rejected_from_status`）
- ✅ 承包商运力报备 CRUD（含 capability_tags JSONB）
- ✅ 修井运行表 CRUD + 待派工优先排序（approved_at + production_priority）
- ✅ Redis 分布式锁防重复派工（TTL 30s + 自动释放）
- ✅ 施工进度更新 + 状态自动推进（DISPATCHED → WORKING → FINISHED）
- ✅ A5 SSO 单点登录令牌生成（JWT + 5 分钟有效期）
- ✅ A5 RESTful 回调接收（HMAC 签名验证）+ 工单状态同步
- ✅ A5 数据清洗引擎（Pandas 去重 / 日期格式化 / 缺失值填充）
- ✅ Celery 定时任务每 30 分钟同步 A5 数据（含 3 次重试 + 告警）
- ✅ 防偏磨系统 HTTP 客户端（含本地模拟模式）
- ✅ 工程设计规则引擎（5 项校验规则）
- ✅ python-docx Word 文档模板渲染
- ✅ openpyxl Excel 报表渲染
- ✅ MinIO 对象存储归档（自动版本号 v1/v2/v3…）
- ✅ 工程设计文档 CRUD + 预签名下载链接
- ✅ 本地无 A5/FPM/MinIO 时降级联调通过
- ✅ 系统管理前端：用户、角色、菜单、权限、操作日志入口逐页验证通过
- ✅ `POSTGRES_PASSWORD=dummy JWT_SECRET_KEY=dummy-secret ADMIN_INITIAL_PASSWORD='ChangeMe_123!' python -m compileall -q app main.py celery_app.py`

## 本地运行时仪表盘

项目根目录的 `runtime-dashboard.html` 提供了本地运行时状态可视化面板，可直观查看：
- 数据库连接状态与版本
- Redis 连接状态
- Alembic 迁移状态
- API 端点健康检查
- 前端构建状态

使用方式：启动后端后，浏览器打开 `runtime-dashboard.html` 即可查看实时状态。
