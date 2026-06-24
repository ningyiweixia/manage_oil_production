# 采油二厂井下作业管理系统

后端采用 `FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL 15(JSONB) + Redis + Celery + JWT + Alembic`。前端采用 `Vue3 + Element Plus + ECharts 5 + TypeScript`。当前已完成全部 5 个模块。

- 模块 1：系统总体底层搭建
- 模块 2：上修项目池管理
- 模块 3：系统基础支撑与管理模块（RBAC + 统一身份认证）
- 模块 4：前端交互与可视化大屏（Vue3 + Element Plus + ECharts）
- 模块 5：跨系统协同与异步引擎（承包商管理 + A5 集成 + 工程设计）

## 项目结构

```text
manage_factory/
  main.py                       # FastAPI 应用入口
  requirements.txt              # Python 依赖
  alembic.ini                   # 数据库迁移配置
  alembic/
    versions/                   # 迁移脚本
  app/
    api/
      deps.py                   # 权限依赖注入
      ws.py                     # WebSocket 审批通知
      v1/
        router.py               # API 路由聚合
        endpoints/
          auth.py               # 登录/登出/刷新令牌/当前用户
          dictionaries.py       # 数据字典 CRUD
          rbac.py               # 用户/角色/菜单/权限管理
          workover_project_pools.py  # 上修项目池核心接口
    core/
      config.py                 # 应用配置（环境变量驱动）
      exceptions.py             # 全局异常处理
      middleware.py              # JWT 鉴权 + 操作日志中间件
      redis.py                  # Redis 缓存客户端（自动降级）
      security.py               # JWT 签发与解码
      status_codes.py           # 业务状态码常量
    crud/
      dictionary.py             # 数据字典 CRUD
      rbac.py                   # RBAC CRUD
      workover_project_pool.py  # 项目池 CRUD + 状态机 + 智能路由
    db/
      base.py                   # ORM 基类与命名规范
      seed.py                   # 初始化种子数据
      session.py                # 数据库会话
    models/
      approval.py               # 审批日志
      dictionary.py             # 数据字典
      engineering.py            # 工程设计文档
      rbac.py                   # 用户/角色/菜单/权限/操作日志
      workover.py               # 上修项目池/施工单/承包商能力
    schemas/
      auth.py                   # 认证请求/响应
      dictionary.py             # 字典 Schema
      pagination.py             # 分页模型
      rbac.py                   # RBAC Schema
      response.py               # 统一响应
      workover_project_pool.py  # 项目池 Schema
    services/
      audit_service.py          # 审批日志写入
      auth_service.py           # 认证服务（令牌撤销/权限缓存）
      dictionary_service.py     # 字典值校验
      notification_service.py   # WebSocket 待办推送
      rbac_service.py           # RBAC 业务逻辑
      workover_analytics_service.py  # 统计分析聚合
      workover_project_pool_excel.py # Excel 导入导出
      # ——— 模块五：跨系统协同与异步引擎 ———
      a5_client.py              # A5 系统 HTTP 客户端（httpx）
      a5_auth_service.py        # A5 SSO 单点登录令牌生成
      a5_data_cleaner.py        # A5 数据清洗引擎（Pandas）
      a5_sync_service.py        # A5 数据同步服务（日报/异常/工序）
      contractor_service.py     # 承包商状态管理
      design_rule_engine.py     # 工程设计规则引擎
      dispatch_service.py       # Redis 分布式派工锁
      engineering_design_service.py  # 工程设计文档生成服务
      fpm_client.py             # 防偏磨设计系统 HTTP 客户端
      template_renderer.py      # 模板渲染 + MinIO 存储
    tasks/
      __init__.py
      a5_tasks.py               # Celery 定时任务（每30分钟同步A5数据）
    utils/
      jsonb.py                  # JSONB 查询辅助
  celery_app.py                 # Celery 分布式任务队列配置
  frontend/
    src/
      api/
        auth.ts                 # 登录接口（含 RBAC 菜单/权限类型）
        dictionary.ts           # 数据字典接口
        http.ts                 # Axios 封装 + JWT 请求头 + 统一解包
        workover.ts             # 项目池/审批接口（含演示模式降级）
      composables/
        useApprovalSocket.ts    # WebSocket 待办弹窗提醒
        useProjectSync.ts       # 项目数据同步 + 通知消息格式化
      router/
        index.ts                # 前端路由（登录/工作台/大屏）+ JWT 守卫
      styles/
        main.css                # 全局样式
      types/
        workover.ts             # TypeScript 类型定义
      utils/
        status.ts               # 审批状态/流转/标签工具函数
      views/
        LoginView.vue           # 登录页
        MainLayout.vue          # 主布局（动态 RBAC 侧边栏+顶栏+通知）
        ApprovalWorkbench.vue   # 审批工作台（权限按钮守卫）
        AnalyticsDashboard.vue  # 统计分析大屏
    index.html                  # HTML 入口
    vite.config.ts              # Vite 构建配置
  deploy/
    frontend-dist/              # 前端构建产物
    nginx/                      # Nginx 配置（DMZ + 前端站点）
    prometheus/                 # Prometheus 配置与告警规则
    grafana/                    # Grafana 仪表板与数据源
    scripts/
      deploy.sh                 # 一键部署脚本
    README.md                   # 部署说明
  docker-compose.yml            # 容器编排
```

## 本地运行

### 后端

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 确保 PostgreSQL 已启动，数据库 manage_factory 已创建
alembic upgrade head
python -m app.db.seed
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

访问入口：

- 健康检查：`GET http://127.0.0.1:8000/health`
- Swagger 文档：`http://127.0.0.1:8000/docs`
- Prometheus 指标：`http://127.0.0.1:8000/metrics`

### 前端

```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

访问入口：

- 前端开发服务：`http://127.0.0.1:5173`
- 默认代理后端：`http://127.0.0.1:8000/api/v1`
- WebSocket 代理：`ws://127.0.0.1:8000/ws`

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
ACCESS_TOKEN_EXPIRE_MINUTES=120
REFRESH_TOKEN_EXPIRE_MINUTES=10080
AUTH_WHITELIST_PATHS=/docs,/openapi.json,/health,/metrics
CORS_ALLOW_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

> `.env` 已加入 `.gitignore`，禁止提交。Redis 不可用时自动降级为进程内缓存。

## 统一接口规范

所有业务接口统一返回：

```json
{"code": 20000, "msg": "success", "data": {}}
```

业务码：

| 状态码 | 含义 | HTTP |
|--------|------|------|
| `20000` | 成功 | 200 |
| `40001` | 参数错误 | 400 |
| `40100` | 登录失效 | 401 |
| `40300` | 越权访问 | 403 |
| `40900` | 业务冲突 | 409 |
| `42900` | 请求过频 | 429 |
| `60001` | A5 系统联动失败 | 502 |

## 环境变量（A5 系统集成 & MinIO 对象存储）

```env
# A5 系统集成配置
A5_BASE_URL=http://a5-internal:8080
A5_API_KEY=your-api-key
A5_API_SECRET=your-api-secret

# MinIO 对象存储配置
MINIO_ENDPOINT=127.0.0.1:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_ENGINEERING=engineering-designs
MINIO_BUCKET_TEMPLATES=design-templates

# 防偏磨设计系统配置
FPM_BASE_URL=http://fpm-system:9090
```

> A5 系统的 `AUTH_WHITELIST` 已包含 `/api/v1/a5/callback` 免鉴权路径，供 A5 系统回调。

## Celery 异步任务

```powershell
# 启动 Celery Worker + Beat（定时任务）
celery -A celery_app worker --loglevel=info --beat
```

Celery 配置：
- 后端/结果存储：`Redis`
- 定时任务：`sync-a5-data-every-30min`（每 30 分钟拉取 A5 日报/异常/工序数据，方案强制要求）
- 失败重试：最多 3 次，间隔 60 秒
- 连续失败 3 次触发企业微信告警

## 系统基础支撑与管理模块（RBAC）

### 认证接口

```text
POST /api/v1/auth/login      登录，返回用户信息、权限、菜单和令牌
POST /api/v1/auth/refresh    刷新 access token
POST /api/v1/auth/logout     登出并吊销 refresh token
GET  /api/v1/auth/me         当前用户信息
```

### RBAC 管理接口

```text
GET    /api/v1/users                  用户列表
POST   /api/v1/users                  新增用户
PUT    /api/v1/users/{user_id}        编辑用户
PATCH  /api/v1/users/{user_id}/active 启停用户
PATCH  /api/v1/users/{user_id}/roles  分配角色
DELETE /api/v1/users/{user_id}        删除用户（软删除）

GET    /api/v1/roles                  角色列表
POST   /api/v1/roles                  新增角色
PUT    /api/v1/roles/{role_id}        编辑角色
PATCH  /api/v1/roles/{role_id}/menus       分配菜单
PATCH  /api/v1/roles/{role_id}/permissions 分配权限
DELETE /api/v1/roles/{role_id}        删除角色

GET    /api/v1/menus                  菜单列表（树形）
POST   /api/v1/menus                  新增菜单
PUT    /api/v1/menus/{menu_id}        编辑菜单
DELETE /api/v1/menus/{menu_id}        删除菜单

GET    /api/v1/permissions            权限列表
POST   /api/v1/permissions            新增权限
PUT    /api/v1/permissions/{permission_id}   编辑权限
DELETE /api/v1/permissions/{permission_id}   删除权限

GET    /api/v1/operation-logs         操作日志
```

### 数据字典

```text
GET    /api/v1/dictionaries/               字典列表（支持 dict_type 筛选）
POST   /api/v1/dictionaries/               新增字典项
PUT    /api/v1/dictionaries/{id}           编辑字典项
PATCH  /api/v1/dictionaries/{id}/active    启停字典项
```

字典表维护措施类型、施工工序等业务枚举，接口层通过 `ensure_dictionary_values` 强制校验。

## 上修项目池管理模块

### 审批状态流转

```
DRAFT → PENDING_GEOLOGY_VERIFY → PENDING_PROCESS_VERIFY → APPROVED → DISPATCHED
  ↑              ↓                        ↓
  └── REJECTED ← ─────────────────────────┘
         ↓
      VOIDED
```

### 状态转换规则

| 当前状态 | 允许转换到 |
|----------|-----------|
| DRAFT | PENDING_GEOLOGY_VERIFY, VOIDED |
| PENDING_GEOLOGY_VERIFY | PENDING_PROCESS_VERIFY, REJECTED |
| PENDING_PROCESS_VERIFY | APPROVED, REJECTED |
| APPROVED | DISPATCHED, VOIDED |
| REJECTED | DRAFT, PENDING_GEOLOGY_VERIFY, PENDING_PROCESS_VERIFY, VOIDED |

### 智能路由：驳回后重新提报

从驳回状态重新提报时，系统自动从审批日志中查找驳回前的审批节点：
- 在地质核实被驳回 → 重新提交至 **地质核实**
- 在工艺核实被驳回 → 重新提交至 **工艺核实**

### 主要接口

```text
GET    /api/v1/workover-project-pools/               列表（分页、筛选）
GET    /api/v1/workover-project-pools/{id}           详情
POST   /api/v1/workover-project-pools/               新增（草稿）
PUT    /api/v1/workover-project-pools/{id}           编辑
DELETE /api/v1/workover-project-pools/{id}           删除（软删除，标记作废）
PATCH  /api/v1/workover-project-pools/submit         批量提交至审批
PATCH  /api/v1/workover-project-pools/{id}/status    审批通过/驳回/重新提报
POST   /api/v1/workover-project-pools/import         Excel 导入
GET    /api/v1/workover-project-pools/export/all     Excel 导出
GET    /api/v1/workover-project-pools/analytics/summary  统计分析
```

### 筛选参数

- `page` / `page_size`：分页
- `status`：审批状态
- `well_no`：井号（模糊匹配）
- `block_name`：区块（模糊匹配）
- `measure_type`：措施类型（字典值精确匹配）

### 返回字段

项目列表返回 `rejected_from_status` 字段，标明驳回项目在被驳回前所处的审批节点，前端据此区分「地质驳回」与「工艺驳回」。

## 跨系统协同与异步引擎（模块五）

### 承包商队伍管理与调度模块

#### 智能派工排序

派工接口严格按以下规则排序（方案强制要求）：
- 审批通过时间升序（先审批的优先派工）
- 产量优先级降序（高优先级优先）

#### Redis 分布式锁防重机制

```
PATCH /api/v1/contractors/dispatch
```

为防止多个调度员同时将两口井派给同一支队伍，派工接口强制引入 Redis 分布式排他锁：
- 锁 KEY 格式：`dispatch:lock:{contractor_capacity_id}`
- 锁过期时间：30 秒（防死锁）
- 加锁失败返回 `40900` 并发冲突提示

#### 施工进度状态机

```
WAITING_DISPATCH → DISPATCHED → WORKING → FINISHED
                         ↓                  ↓
                      CANCELED           CANCELED
```

进度到达 100% 时自动推进状态：
- DISPATCHED → WORKING（actual_start_at 自动填入）
- WORKING → FINISHED（actual_end_at 自动填入）

#### 主要接口

```text
GET    /api/v1/contractors/                              承包商运力列表（分页）
POST   /api/v1/contractors/                              新增承包商运力报备
GET    /api/v1/contractors/{id}                           运力详情
PUT    /api/v1/contractors/{id}                           更新运力报备

GET    /api/v1/contractors/priority-sheets                待派工优先顺序列表
GET    /api/v1/contractors/operation-sheets/              修井运行表列表（分页）
POST   /api/v1/contractors/operation-sheets/              创建修井运行表
GET    /api/v1/contractors/operation-sheets/{id}          运行表详情
PATCH  /api/v1/contractors/dispatch                       派工分配队伍（Redis 分布式锁）
PATCH  /api/v1/contractors/operation-sheets/{id}/progress 更新施工进度
```

### A5 系统集成与互操作模块

#### 集成架构

```
SSO 跳转（主动）      → 前端携带令牌直接跳转 A5 系统工单页面
状态回调（被动）      → A5 工单审核/办结时 RESTful 回调本系统
定时同步（主动）      → Celery 每 30 分钟拉取 A5 日报/异常/工序数据
```

#### API 约束

- 所有集成接口使用 HTTPS + Token 身份双重鉴权
- 回调接口 `/api/v1/a5/callback` 加入 `AUTH_WHITELIST` 免鉴权，由签名验证保障安全
- 配置 IP 白名单访问限制
- 全量接口调用自动落地日志

#### 主要接口

```text
POST  /api/v1/a5/callback                 接收 A5 系统工单状态回调
POST  /api/v1/a5/sso-token                生成 SSO 跳转令牌（5 分钟有效）
GET   /api/v1/a5/sync/status              查看最近一次同步状态
POST  /api/v1/a5/sync/trigger             手动触发一次全量数据同步
```

#### Celery 定时任务

- `sync-a5-data-every-30min`：每 30 分钟自动轮询拉取 A5 系统数据
- 拉取内容：作业日报、施工异常、工序进度
- 失败机制：最多重试 3 次，连续失败 3 次触发企业微信告警
- 数据清洗：基于 Pandas 进行去重、日期格式化、缺失值填充

#### SSO 跳转流程

```text
前端点击"跳转A5" → 请求 /api/v1/a5/sso-token → 后端签发 JWT 临时令牌
→ 返回 redirect_url（含 token + well_no） → 前端跳转 A5 系统
→ A5 验证令牌后展示工单操作页面
```

### 工程设计管理模块

#### 生成流程

```
获取项目信息 → 调防偏磨系统获取偏磨参数 → 规则引擎校验
→ 生成版本号 → 模板渲染（python-docx/openpyxl） → MinIO 归档 → 写审计日志
```

#### 规则引擎

内置规则库，校验不通过直接阻断生成：

| 规则 | 说明 |
|------|------|
| 抽油机型号匹配 | 井深 > 3000m 必须使用特定型号抽油机 |
| 措施冲突检测 | 酸化和冲砂洗井不能同工序进行 |
| 施工参数范围 | 压力 0-100MPa，温度 -50~500°C |
| 防偏磨参数完整性 | 必须包含 casing_diameter, tubing_size, wear_level |
| 防偏磨严重程度 | wear_level=SEVERE 时阻断生成 |

#### 文档版本管理

- 版本号格式：`v1`, `v2`, `v3`...
- 同一井号自动递增版本号
- 数据库 UniqueConstraint(`well_no`, `version`) 保证版本唯一

#### 主要接口

```text
GET    /api/v1/engineering-designs/                 工程设计文档列表（分页）
POST   /api/v1/engineering-designs/generate         一键生成工程设计文档
GET    /api/v1/engineering-designs/{id}             文档详情
GET    /api/v1/engineering-designs/{id}/download    获取 MinIO 临时下载链接
DELETE /api/v1/engineering-designs/{id}             删除文档
POST   /api/v1/engineering-designs/check-rules      手动触发规则校验
```

## 前端交互与可视化大屏

### 审批工作台

- 项目池列表：多条件筛选、分页、优先级进度条、措施标签、审批流步骤条
- 批量提交：勾选草稿项目，一键提交至地质核实
- 审批操作：通过（流转到下一节点）、驳回（退回修改）
- 重新提报：已驳回项目重新提交，根据 `rejected_from_status` 智能路由到地质核实或工艺核实
- 删除项目：确认对话框，软删除标记作废
- 措施 JSONB 表单：动态增删措施行，措施类型下拉从字典 API 加载
- WebSocket 待办：页面加载后自动连接 `/ws/approval`，收到推送时弹窗提醒

### 统计分析大屏

- KPI 卡片：项目总数、待审批数、审批通过率、预计总费用、平均优先级
- 审批状态柱状图
- 措施类型饼图
- 区块 × 状态热力图
- 日提报趋势折线图
- 图表一键导出 PNG

### RBAC 菜单集成（与模块三联动）

- 登录时从后端获取用户菜单树（`menus`）和权限列表（`permissions`）
- 侧边栏菜单由后端 RBAC 数据动态驱动，支持父子嵌套、图标映射、不可见菜单过滤
- 操作按钮（新增/编辑/提交/审批/删除）根据用户权限自动显示/隐藏
- 当后端 RBAC 数据不可用时，自动回退为静态菜单

### 权限按钮映射

| 按钮 | 所需权限 |
|------|----------|
| 新增提报 | `workover_project_pool:create` |
| 编辑项目 | `workover_project_pool:update` |
| 批量提交 | `workover_project_pool:submit` |
| 通过 / 驳回 | `workover_project_pool:approve` |
| 删除项目 | `workover_project_pool:delete` |

### 演示模式

当后端不可用时，前端自动降级为演示模式（使用 localStorage 存储数据），便于前端页面展示和联调。连接后端后自动切换为正常模式。

### WebSocket 消息格式

```json
{
  "title": "审批待办提醒",
  "message": "CY2-136 已提交至地质核实",
  "node_code": "PENDING_GEOLOGY_VERIFY",
  "type": "info"
}
```

## Alembic 迁移

```powershell
alembic upgrade head          # 升级到最新
alembic downgrade -1          # 回退一个版本
alembic revision --autogenerate -m "描述"
```

当前迁移：

| 版本 | 内容 |
|------|------|
| `20260531_0001` | 核心底层表 |
| `20260602_0002` | 上修项目池管理模块 |
| `20260604_0003` | 系统基础支撑与 RBAC 模块 |
| `20260616_0004` | 安全与数据完整性修复 |

## 容器化部署

完整 Docker Compose 编排、Nginx 反向代理、监控体系见 `deploy/` 目录。

```powershell
# 一键部署
.\deploy\scripts\deploy.ps1
```

主要服务：

| 服务 | 地址 |
|------|------|
| 应用入口 | `https://localhost/` |
| 后端健康检查 | `https://localhost/health` |
| Grafana 监控 | `https://localhost/grafana/` |
| Prometheus | `https://localhost/prometheus/` |

网络分区：

- DMZ 区：Nginx（HTTPS 终结、安全头、限流）
- APP 区：FastAPI 后端、Vue3 前端、Prometheus、Grafana
- DB 区：PostgreSQL、Redis、MinIO

详见 `deploy/README.md`。

## 安全说明

- `.env`、`.local/`、日志、虚拟环境、缓存文件已加入 `.gitignore`
- 所有查询使用参数化，禁止裸 SQL 拼接
- 高危操作（编辑/删除/提报/审批）自动写入 `approval_log` 审计日志
- JWT 全局鉴权 + 路由级 RBAC 权限校验
- 操作日志记录用户、IP、方法、路径、权限标识、返回码
- 生产环境 CSP 由 Nginx 注入；开发模式放宽以便 Vite HMR 正常工作
- 禁止提交 `frontend/src/**/*.js` / `*.js.map`（已加入 `.gitignore`），避免过期编译产物覆盖 TypeScript 源码
- 生产部署建议通过 Nginx 暴露 DMZ 入口，FastAPI 运行于 APP 区，PostgreSQL/Redis 运行于 DB 区

## 验证记录

- ✅ `pip install -r requirements.txt`
- ✅ `alembic upgrade head`
- ✅ `python -m app.db.seed`
- ✅ 登录/刷新/登出/当前用户
- ✅ 用户/角色/菜单/权限 CRUD
- ✅ 数据字典 CRUD
- ✅ 项目池 CRUD + 提交 + 审批 + 驳回 + 重新提报
- ✅ 智能路由（地质驳回 → 地质重提，工艺驳回 → 工艺重提）
- ✅ 操作日志自动写入
- ✅ WebSocket 审批待办推送
- ✅ Excel 导入导出
- ✅ 统计分析 API
- ✅ `npm install && npm run build`
- ✅ `vue-tsc --noEmit` TypeScript 类型检查零错误
- ✅ Vue3 前端构建产物输出到 `deploy/frontend-dist/`
- ✅ RBAC 菜单动态渲染 + 权限按钮守卫
- ✅ 驳回重提智能路由（前端使用 `rejected_from_status`）
- ✅ 承包商运力报备 CRUD（创建/更新/查询）
- ✅ 修井运行表 CRUD + 待派工优先排序
- ✅ Redis 分布式锁防重复派工（TTL 30s + 自动释放）
- ✅ 施工进度更新 + 状态自动推进（DISPATCHED→WORKING→FINISHED）
- ✅ A5 SSO 单点登录令牌生成（JWT + 5 分钟有效期）
- ✅ A5 RESTful 回调接收 + 工单状态实时同步
- ✅ A5 数据清洗引擎（Pandas 去重/日期格式化/缺失值填充）
- ✅ Celery 定时任务每 30 分钟同步 A5 数据（含 3 次重试 + 告警）
- ✅ 防偏磨系统 HTTP 客户端（含本地模拟模式）
- ✅ 工程设计规则引擎（5 项校验规则）
- ✅ python-docx Word 文档模板渲染
- ✅ openpyxl Excel 报表渲染
- ✅ MinIO 对象存储归档（自动版本号 v1/v2/v3...）
- ✅ 工程设计文档 CRUD + 临时下载链接
