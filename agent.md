# 采油二厂井下作业管理系统 - AI Agent 开发上下文文档

## 一、 项目概述

* **项目名称**：采油二厂井下作业管理系统
* **项目定位**：一个集多方协同、多级审批、跨系统联动、数据分析及自动化文档于一体的综合性井下作业全流程线上管理平台
* **核心价值**：实现闭环的业务管理流程，打通底层系统（A5系统及防偏磨系统）壁垒，提升审批进度透明度，并将海量业务数据转化为直观图表赋能决策
* **当前阶段**：核心业务模块全部实现，系统处于功能完善和稳定性增强阶段（对应原路线图阶段五）

## 二、 核心业务流程

该系统包含四个关键业务阶段，开发时需严格遵循此业务逻辑：

1. **上修项目池提报与多级联审**：基层单位录入待修井号至"上修项目池"。项目池管理单位选井提出申请后，依次流转至地质所/生产指挥中心（产量核实）、工艺所（井况核实）。审批通过的井进入"修井运行表"资源库等待派发。
2. **队伍状态提报与智能派工**：承包商每日报备可用队伍数量及状态。工艺所调度人员根据优先级和队伍状态，从"修井运行表"提取任务进行分配，分配时需引入并发防重机制（Redis 分布式锁）。
3. **数据抓取与统计分析**：实时/定时抓取外部A5系统中的异常情况、特殊工序等数据，生成图表和定制化报告。
4. **工程设计与系统协同**：调用外部系统（防偏磨设计系统、A5系统）数据，通过内置规则引擎校验后，自动生成并渲染 Word/Excel 标准化工程设计方案。

## 三、 技术栈与总体架构

本项目采用分层解耦的现代化前后端分离架构。AI 在生成代码时必须严格限定在以下技术栈内：

### 后端技术栈
* **Web 框架**：`FastAPI` (Python 3.12 异步 Web 框架)
* **数据库引擎**：`PostgreSQL 15` (利用 `JSONB` 字段存储非结构化工序/措施数据)，本地开发兼容 `SQLite`
* **ORM 与数据校验**：`SQLAlchemy 2.0` (配合 Alembic 迁移管理) + `Pydantic v2`
* **异步任务与缓存中心**：`Celery 5.4` (分布式任务队列, Redis 作为 broker/backend) + `Redis 7.4` (状态缓存/并发悲观锁/JWT 黑名单)
* **数据处理与文档生成**：`Pandas` (数据清洗统计与 Excel 解析) + `python-docx` (Word 工程报告组装) + `openpyxl` (Excel 报表生成)
* **文件存储**：`MinIO` 对象存储 (兼容 S3 协议，用于报告模板与产出文档)，本地开发自动回退到本地文件系统
* **监控与可观测性**：`Prometheus` (指标采集) + `Grafana` (可视化大屏) + `prometheus_fastapi_instrumentator` (FastAPI 指标暴露)

### 前端技术栈
* **核心框架**：`Vue.js 3.5` + `TypeScript 5.7`
* **UI 组件库**：`Element Plus 2.9` (中文 locale)
* **数据可视化**：`ECharts 5.5`
* **HTTP 客户端**：`Axios 1.7` (JWT Bearer 令牌拦截器 + 401 自动跳转)
* **构建工具**：`Vite 8.0`
* **路由管理**：`Vue Router 4.5` (路由守卫拦截非法 URL 访问)

### 架构分层
```
前端 (Vue 3 + Element Plus) → Nginx (DMZ 反代)
  → FastAPI (应用逻辑层) → PostgreSQL + Redis + MinIO (数据层)
  → Celery Worker (异步任务引擎)
  → Prometheus + Grafana (可观测性)
```

## 四、 关键系统集成规范（重要红线）

系统与核心生产系统"A5系统"对接时，必须遵循以下合规约束：

* **操作跳转**：系统配置专属跳转入口，通过 SSO（单点登录）+ 安全令牌鉴权机制无缝跳转至 A5 系统完成工单下发，无需重复登录。SSO 令牌生成逻辑已实现于 `a5_auth_service.py`。
* **状态回调**：A5 系统内工单状态变更（审核、办结等）后，通过 RESTful 接口主动回调本系统的专属 API。回调接口已实现 HMAC 签名校验（`/a5/callback`），确保回调来源可信。
* **数据抓取底线**：严禁使用 WebScraping 爬虫技术。必须采用 `Celery` 定时轮询拉取 A5 提供的正式 REST API 或数据库只读中间表（Views）。当前实现：Celery Beat 每 30 分钟触发 `sync_a5_data_task` 任务。
* **接口规范**：全面推行 RESTful 风格（名词复数路由），局部更新强制使用 `PATCH`（如审批流转）。所有响应体由 `Pydantic` 约束（包含 `code`, `msg`, `data`），统一使用 `ApiResponse[T]` 泛型包装。
* **外部系统客户端**：A5 系统客户端（`a5_client.py`）和防偏磨系统客户端（`fpm_client.py`）均通过配置化的 base_url 进行连接，支持环境变量注入。

## 五、 核心数据表与关联模型

数据库模型遵循高内聚、低耦合原则，所有模型继承 `TimestampMixin`（created_at/updated_at）。当前已实现的核心表：

### 业务核心表
| 表名 | 文件 | 用途 |
|---|---|---|
| `workover_project_pool` | `models/workover.py` | 业务源头，存储待修井基础信息及修井措施（JSONB），含完整状态机 |
| `workover_operation_sheet` | `models/workover.py` | 核心执行表，关联项目池主键与承包商运力，记录作业进度（0-100） |
| `contractor_capacity` | `models/workover.py` | 管理外包队伍资源，记录每日运力报备与队伍状态（AVAILABLE/BUSY/OFFLINE） |
| `engineering_design_doc` | `models/engineering.py` | 关联井号，记录文档版本号、MinIO bucket/object_key 及 checksum |
| `approval_log` | `models/approval.py` | 实现全流程审批溯源留痕，记录变更前后 JSONB 数据快照 |

### RBAC 权限体系表
| 表名 | 文件 | 用途 |
|---|---|---|
| `sys_user` | `models/rbac.py` | 用户表，含部门/手机/邮箱/超级管理员标记/扩展配置，M2M 关联角色 |
| `sys_role` | `models/rbac.py` | 角色表，含角色编码/扩展配置，M2M 关联用户/菜单/权限 |
| `sys_menu` | `models/rbac.py` | 菜单表，支持自引用父子树形结构，含路由名/路径/组件/图标/排序 |
| `sys_permission` | `models/rbac.py` | 权限表，按路径+方法（GET/POST/PATCH/DELETE）定义接口级权限 |
| `sys_operation_log` | `models/rbac.py` | 操作日志表，记录用户/IP/方法/路径/请求体/响应消息 |

### 数据字典表
| 表名 | 文件 | 用途 |
|---|---|---|
| `data_dictionary` | `models/dictionary.py` | 动态数据维表，存储井号资源库/修井措施类型库/工序标准库等下拉选项 |

### 关联关系（ORM 约束）
* **一对多**：`workover_project_pool` → `workover_operation_sheet`（一个项目可衍生多次作业）
* **多对一**：`workover_operation_sheet` → `contractor_capacity`（一支队伍可承接多个不冲突的作业）
* **多对多**：用户 ↔ 角色 ↔ 菜单/权限（通过 `user_roles`/`role_menus`/`role_permissions` 中间表）
* **一对多溯源**：`approval_log` 通过 `business_type` + `business_id` 关联各业务表

## 六、 安全与权限控制

### 认证体系
* 采用 `JWT` 动态令牌机制（access_token + refresh_token 双令牌），兼容企业 SSO 与 LDAP
* `passlib` (pbkdf2_sha256) 密码哈希，`python-jose` 进行 JWT 签发与验证
* Redis 实现的 JTI（JWT ID）吊销机制：主动登出时将令牌加入黑名单，支持即时失效

### 权限控制
* `RBAC` 角色权限控制体系：用户 → 角色 → 菜单 + 权限（接口级），三级粒度管控
* 内置核心业务角色（Seed Data）：项目池管理员、业务审核员、承包商操作人员、运维管理员、超级管理员
* 前端路由守卫：Vue Router `beforeEach` 钩子检查 JWT 有效期，过期自动跳转登录页
* 后端双重校验：`AuthMiddleware`（全局 JWT 校验）+ `require_permission` 依赖注入（接口级权限校验）

### 安全中间件
* `AuthMiddleware`：全局拦截所有请求（白名单路径除外），校验 Authorization Bearer 令牌，将当前用户注入 `request.state.user`
* `OperationLogMiddleware`：最佳努力（best-effort）审计日志记录，记录所有 API 调用的请求/响应信息

### A5 系统双重安全边界
* **跳转安全**：SSO 令牌生成包含安全令牌与唯一 URL 参数的双向绑定校验
* **接口白名单**：所有 API 接口除 HTTPS + Token 鉴权外，需在网关层面配置 IP 白名单
* **回调安全**：A5 回调接口实现 HMAC 签名验证，防止伪造回调

## 七、 实时交互与事件驱动要求

### WebSocket 全双工通信
* **实现位置**：`app/api/ws.py` + `services/notification_service.py`
* **端点**：`/ws/approval`（需 JWT 认证）
* **连接管理**：`ApprovalConnectionManager` 管理活跃连接池，支持广播消息
* **推送事件**："工艺所审核通过"、"调度派工完毕"、"工单被驳回"等核心业务节点
* **前端集成**：`useApprovalSocket.ts` composable，支持指数退避自动重连（最多 6 次），auth handshake 协议

### 异常告警推送
* 内置异常检测引擎：A5 同步连续失败检测（连续 3 次失败触发告警）
* 告警通道：预留企业微信 Webhook 推送接口
* Prometheus 告警规则：后端宕机（2分钟）、高 API 延迟（p95 > 1s 持续 5 分钟）、磁盘空间 < 15%、高 CPU

## 八、 核心业务状态机（重要开发红线）

在生成具体的业务逻辑代码时，必须遵循以下状态与架构模式设计：

### 项目池状态机
```
DRAFT → PENDING_GEOLOGY_VERIFY → PENDING_PROCESS_VERIFY → APPROVED → DISPATCHED
  ↓         ↓                        ↓                      ↓
VOIDED   REJECTED  ←──────────────  REJECTED             CANCELED
```
* **状态转换管控**：`crud/workover_project_pool.py` 中的 `ALLOWED_STATUS_TRANSITIONS` 字典严格定义了合法状态流转路径
* **驳回智能路由**：从 REJECTED 状态重新提交时，系统根据驳回节点自动路由回正确的审核节点（而非从零开始）
* **审批留痕**：每次状态变更在 `approval_log` 表记录 before/after JSONB 数据快照，包含操作人/操作类型/审批意见

### 承包商/运力状态
* 队伍状态：`AVAILABLE` → `BUSY` → `OFFLINE`
* 运力报备必须传入"特定施工能力"标签字段（JSONB `capability_tags`，如大修资质）

### 作业运行表状态
* `WAITING_DISPATCH` → `DISPATCHED` → `WORKING` → `FINISHED`
* 可中途 `CANCELED`
* 进度更新到 100% 时自动触发状态变更为 FINISHED

### 状态枚举常量
* 业务流转必须使用严谨的英文状态枚举（Enum），严禁使用魔术字符串
* 当前实现：`ProjectPoolStatus`、`OperationSheetStatus`、`CapacityStatus`、`ApprovalAction` 等

## 九、 API 端点架构

### 路由组织
```
/api/v1/auth/          — 认证（login/refresh/logout/me）
/api/v1/users/         — 用户管理（RBAC）
/api/v1/roles/         — 角色管理（RBAC）
/api/v1/menus/         — 菜单管理（RBAC）
/api/v1/permissions/   — 权限管理（RBAC）
/api/v1/operation-logs/— 操作日志查询
/api/v1/workover-project-pools/ — 上修项目池（CRUD/提交/审批/Excel导入导出/分析）
/api/v1/contractors/   — 承包商运力（CRUD/派工/进度更新）
/api/v1/dictionaries/  — 数据字典（CRUD）
/api/v1/engineering-designs/ — 工程设计文档（生成/下载/规则校验）
/api/v1/a5/            — A5系统集成（回调/SSO/同步）
/ws/approval           — WebSocket 实时推送
/metrics               — Prometheus 指标暴露
/health                — 健康检查
```

### API 标准生命周期（6步法）
所有核心业务 API 必须严格遵循：`请求发起 → 身份认证（AuthMiddleware）→ 参数校验（Pydantic v2）→ 事务执行 → 操作留痕（OperationLogMiddleware + approval_log）→ 结果返回`

### 业务状态码字典
严禁仅使用基础 HTTP 状态码。业务返回必须使用自定义状态码：
* `20000` — 成功
* `40001` — 参数错误
* `40100` — 身份失效
* `40300` — 越权访问
* `40900` — 并发冲突
* `50300` — 数据库不可用
* `60001` — 外部A5联动失败
* `60002` — 外部防偏磨系统联动失败

## 十、 Celery 异步任务架构

### 任务配置
* **Broker/Backend**：Redis
* **序列化**：JSON
* **时区**：Asia/Shanghai
* **任务超时**：10 分钟
* **Beat 调度**：`sync_a5_data_task` 每 30 分钟执行一次

### 当前任务清单
| 任务 | 文件 | 说明 |
|---|---|---|
| `sync_a5_data_task` | `tasks/a5_tasks.py` | A5 数据全量同步，含 3 次重试，连续 3 次失败触发告警 |
| `sync_anomaly_task` | `tasks/a5_tasks.py` | 手动触发的异常数据同步 |

## 十一、 工程设计与规则引擎

### 文档生成流水线
`engineering_design_service.py` 实现完整的文档生成流水线：
1. 查询项目池信息
2. 调用防偏磨系统（FPM）获取参数
3. 执行规则引擎校验（`design_rule_engine.py`）
4. 自动生成版本号
5. 渲染文档模板（`template_renderer.py`）
6. 存入 MinIO 对象存储
7. 写入审计日志

### 规则引擎校验项
* 泵深匹配检查
* 措施冲突检测（如酸化 + 冲砂不可同时执行）
* 施工参数合理性验证
* FPM 数据完整性检查
* 严重偏磨检测

### 文档类型
* Word 工程报告（`python-docx`，支持表格）
* Excel 报表（`openpyxl`）

## 十二、 数据分析与统计模块

### 后端分析引擎
* **服务**：`services/workover_analytics_service.py`
* **技术实现**：基于 Pandas 构建底层处理引擎，将前端传入的多维查询参数自动解析并转换为标准化 DSL 查询语句进行统一筛选与聚合计算
* **严禁**：裸写 SQL 拼接处理多条件查询

### 核心业务指标（数据分析锚点）
* 作业产量统计
* 队伍绩效考核
* 异常工单分布
* 工序耗时分析

### 前端可视化
* KPI 卡片（总项目数、待审批数、审批通过率、预估费用）
* 状态分布柱状图
* 措施类型分布饼图
* 区块-状态热力图
* 每日趋势折线/柱状混合图
* 图表导出为 PNG，数据摘要导出为文本

## 十三、 服务层架构（降级与容错设计）

系统已实现以下容错机制，AI 开发新功能时需保持此设计模式：

### 优雅降级
* **Redis 缓存降级**：`core/redis.py` 中的 `CacheClient`，当 Redis 不可用时自动回退到内存字典（线程安全），保证核心业务不中断
* **MinIO 存储降级**：`services/template_renderer.py` 中的 MinIO 客户端，当 MinIO 不可用时自动回退到本地文件系统
* **数据库兼容**：`db/session.py` 中 SQLite JSONB 兼容适配（编译为 JSON 类型），支持本地开发使用 SQLite 替代 PostgreSQL

### 分布式锁
* **实现**：Redis SET NX 实现并发悲观锁
* **使用场景**：调度派工操作，防止同一任务被多次分配

### 限流控制
* **登录接口**：内存滑动窗口限流（每 IP 每 5 分钟最多 5 次）
* **Nginx 层面**：API 整体限流（20 req/s），burst 40

## 十四、 微观业务规则与参数硬性约束

AI 在编写核心逻辑时，必须严格遵守以下业务参数与规范，严禁自由发挥或常规化硬编码：

* **定时抓取频率**：Celery 定时拉取 A5 系统日报及异常数据的轮询频率硬性设置为 **每 30 分钟** 一次
* **反硬编码与数据字典**：严禁写死下拉框选项。"井号资源库"、"修井措施类型库"、"工序标准库"必须通过 `data_dictionary` 表进行动态管理，提供前后端动态加载接口
* **深度安全审计**：权限变更、工程文档覆盖等高危操作，审计探针强制记录变更前后数据快照（Data Snapshot），存储于 `approval_log.before_snapshot` 和 `after_snapshot` JSONB 字段
* **派工排序逻辑**：智能派工推荐接口的排序必须严格基于 `approved_at`（审批通过时间）与 `production_priority`（产量优先级）字段联合排序
* **JSONB 索引优化**：为存储非结构化"修井措施"的 JSONB 字段主动创建 `GIN` 索引，保障检索性能
* **Excel 解析引擎**：项目池"批量导入"功能必须基于 `Pandas` 库对上传的 Excel 模板进行批量解析与数据清洗（`workover_project_pool_excel.py`），含公式消毒处理
* **文档版本自动控制**：所有经系统自动渲染生成的工程设计文档，在落盘存入 MinIO 前强制生成并记录文档版本号
* **前端路由与 JWT 黑名单**：Vue Router 路由守卫拦截非法访问；FastAPI 实现基于 Redis 的 JWT 吊销机制（主动登出失效）
* **运力表单核心字段**：承包商动态报备接口强制要求传入"特定施工能力"标签字段（`capability_tags` JSONB）

## 十五、 部署架构与网络规划

AI Agent 在生成 IaC、部署脚本或配置反向代理时，必须符合以下架构规划：

### 容器化交付
* **编排**：Docker Compose（11 个服务）
* **应用服务器**：`Uvicorn` 管理 FastAPI 并发
* **反向代理**：`Nginx 1.27-alpine` 负责 SSL 终结、反向代理、静态资源分发、CORS 策略、安全头注入

### 四层网络安全域隔离
```
┌─────────────────────────────────────────────────────┐
│  dmz_net (前端接入域 - 暴露宿主机端口)                │
│  nginx (HTTPS:443, rate limiting, HSTS, CSP)        │
├─────────────────────────────────────────────────────┤
│  app_net (应用逻辑域 - 内部隔离)                      │
│  backend (FastAPI:8000) + frontend (静态SPA)         │
│  + prometheus + grafana + cadvisor + node-exporter   │
├─────────────────────────────────────────────────────┤
│  db_net (核心数据域 - 内部隔离, 绝对禁止外部直接访问)  │
│  postgres:5432 + redis:6379 + minio:9000/9001        │
├─────────────────────────────────────────────────────┤
│  monitor_net (监控域 - 内部隔离)                      │
│  prometheus + grafana + cadvisor + node-exporter     │
└─────────────────────────────────────────────────────┘
```

### 服务资源配置
| 服务 | 推荐配置 | 副本数 |
|---|---|---|
| Nginx 网关 | 4核/8GB | 2+ |
| FastAPI 后端 | 8核/16GB | 2+ |
| PostgreSQL | 16核/32GB | 主从热备 |
| Redis | — | 3+ 集群节点 |
| MinIO | — | 3+ 分布式节点 |

### 监控栈
* **Prometheus**：15 秒采集间隔，30 天数据保留，抓取 backend/cadvisor/node-exporter/nginx/grafana
* **Grafana**：预配置 Prometheus 数据源 + `manage_factory_overview` 仪表盘
* **告警规则**：后端宕机、高延迟、磁盘不足、高 CPU
* **容器指标**：cadvisor + node-exporter

### 数据容灾策略
* 核心业务数据：每日增量备份 + 每周全量备份
* 备份文件需异地/异机存储
* Redis：AOF 持久化

## 十六、 数据库迁移规范

### Alembic 迁移历史（4 个版本）
| 版本 | 日期 | 内容 |
|---|---|---|
| `0001_init_core_tables` | 2026-05-31 | 创建所有核心表及 RBAC 体系 |
| `0002_workover_project_pool_module` | 2026-06-02 | 新增 data_dictionary，重命名字段，添加索引 |
| `0003_system_support_rbac` | 2026-06-04 | 表名单数化，新增 sys_menu + sys_operation_log，扩展字段 |
| `0004_security_integrity_fixes` | 2026-06-16 | 进度约束 (0-100)，审批日志索引，扩展 action 枚举 |

### AI 生成迁移代码规范
* 所有新迁移必须使用 Alembic 自动生成模板
* 必须在迁移中包含 GIN 索引创建（针对 JSONB 字段）
* 迁移必须可逆（提供 `downgrade` 逻辑）

## 十七、 前端架构规范

### 目录结构
```
frontend/src/
  api/           — HTTP API 封装层（http.ts Axios 实例 + 8 个模块文件）
  composables/   — Vue 组合式函数（WebSocket 管理、项目同步事件总线）
  router/        — Vue Router 配置（14 路由 + JWT 守卫）
  styles/        — 全局样式
  types/         — TypeScript 类型定义
  utils/         — 工具函数（状态标签映射、审批流可视化）
  views/         — 9 个页面视图组件
```

### 组件清单
| 视图 | 说明 |
|---|---|
| `LoginView.vue` | 登录表单，调用 `/auth/login` |
| `MainLayout.vue` | 应用外壳：动态菜单（RBAC）+ 通知铃铛（WebSocket 红点） |
| `ApprovalWorkbench.vue` | 项目池管理：搜索/筛选/CRUD/批量提交/审批流转/WebSocket 实时刷新 |
| `AnalyticsDashboard.vue` | ECharts 数据大屏：KPI/图表/热力图/趋势图/导出 |
| `ContractorDispatchView.vue` | 承包商管理：运力报备/优先派工队列/作业进度跟踪 |
| `EngineeringDesignView.vue` | 工程设计：文档生成/规则校验/下载/删除 |
| `A5IntegrationView.vue` | A5 集成：同步状态/手动触发/SSO 跳转令牌 |
| `SystemAdminView.vue` | 系统管理：用户/角色/菜单/权限/日志 Tab 页 CRUD |
| `DictionaryManageView.vue` | 数据字典管理：类型筛选/增删改/启停用 |

### 前端开发规范
* 所有 API 调用通过 `api/http.ts` 中的 Axios 实例，统一处理 Token 注入和 401 重定向
* 使用 `unwrap()` 辅助函数从 `ApiResponse<T>` 信封中提取数据
* 跨组件通信使用 `useProjectSync.ts` 事件总线（`project-data-changed` / `project-notification` 自定义事件）
* WebSocket 连接使用 `useApprovalSocket.ts` composable，包含 auth handshake 和指数退避重连

## 十八、 本地开发环境

### 快速启动
* **环境变量**：复制 `.env.example` 为 `.env`，修改数据库连接等配置
* **后端**：`uvicorn main:app --reload --port 8000`
* **前端**：`cd frontend && npm run dev`（开发服务器端口 5173，自动代理 `/api` 和 `/ws` 到后端）
* **Celery Worker**：`celery -A celery_app worker --loglevel=info`
* **Celery Beat**：`celery -A celery_app beat --loglevel=info`

### 本地开发特性
* **SQLite 兼容**：当 PostgreSQL 不可用时，系统自动使用 SQLite（`local_dev.db`），JSONB 字段自动适配为 JSON
* **Redis 降级**：当 Redis 不可用时，缓存层自动退回到内存字典
* **MinIO 降级**：当 MinIO 不可用时，文件存储自动退回到本地文件系统
* **前端代理**：Vite 开发服务器自动代理 `/api` → `http://localhost:8000`，`/ws` → `ws://localhost:8000`

## 十九、 测试策略

### 当前测试覆盖
* **后端单元测试**：`tests/backend/test_database_unavailable.py` — 验证数据库不可用时的优雅降级（HTTP 503 + 正确错误码）
* **测试框架**：pytest

### AI 编写测试规范
* 新功能必须包含单元测试
* 关键业务路径（审批流转、派工调度、文档生成）需包含集成测试
* 外部依赖（A5、FPM、MinIO）需进行 Mock

## 二十、 项目路线图与实施状态

| 阶段 | 时间 | 内容 | 状态 |
|---|---|---|---|
| 阶段一 | 1-2周 | 蓝图设计、UI原型、基础环境与 CI/CD 搭建 | ✅ 已完成 |
| 阶段二 | 3-6周 | 项目池台账、状态机审批流、队伍状态报备（Alpha版） | ✅ 已完成 |
| 阶段三 | 7-10周 | 对接 A5/防偏磨系统、文档自动化渲染与 MinIO 归档 | ✅ 已完成 |
| 阶段四 | 11-13周 | ECharts 数据大屏、并发压力测试、用户验收测试 (UAT) | ✅ 已完成 |
| 阶段五 | 14周+ | 全量发布与生产环境监控，功能完善与稳定性增强 | 🔄 进行中 |

### 待完善事项
* **测试覆盖**：需要补充单元测试和集成测试（当前仅 1 个测试文件）
* **CI/CD 流水线**：尚未配置 GitHub Actions 或其他 CI/CD 平台
* **Kubernetes 部署**：当前仅有 Docker Compose 编排，需要 K8s manifests（Helm Charts）
* **前端测试**：缺少前端单元测试（vitest）和 E2E 测试（playwright/cypress）
* **Celery 生产部署**：部署脚本需增加 Celery Worker 和 Celery Beat 服务的启动
* **前端错误页面**：缺少 404/500 等错误页面
* **FPM 系统对接**：FPM 客户端已实现，但外部 FPM 系统端点未配置
* **A5 系统对接**：A5 客户端已实现，但外部 A5 系统端点未配置
* **企业微信集成**：告警推送通道已预留，待实际配置 Webhook URL

## 二十一、 种子数据与初始化

### 数据库 Seed
`db/seed.py` 提供完整的初始化数据：
* **17 个菜单项**：系统管理、审批工作台、数据分析、承包商调度、工程设计、A5集成、数据字典等
* **46 个权限项**：覆盖所有 CRUD 操作的接口级权限
* **6 个角色**：超级管理员、项目池管理员、业务审核员、承包商操作人员、运维管理员、普通用户
* **15 个字典条目**：措施类型、区块名称、井况分类等
* **1 个超级管理员**：admin 账号

### 前端演示数据
* 9 个井号的演示数据集（覆盖所有项目池状态），通过 localStorage 持久化

## 二十二、 核心文件索引

### 后端核心文件
| 文件 | 说明 |
|---|---|
| `main.py` | FastAPI 应用入口，挂载中间件/路由/WebSocket/静态文件 |
| `celery_app.py` | Celery 应用配置，Beat 调度定义 |
| `app/core/config.py` | 全局配置（Pydantic Settings，环境变量驱动） |
| `app/core/security.py` | JWT 签发/验证，密码哈希 |
| `app/core/middleware.py` | 认证中间件 + 操作日志中间件 |
| `app/core/redis.py` | Redis 缓存客户端（含降级） |
| `app/core/exceptions.py` | 业务异常类 + 全局异常处理器 |
| `app/core/status_codes.py` | 业务状态码常量 |
| `app/db/session.py` | 数据库引擎/会话工厂 + SQLite JSONB 兼容 |
| `app/db/seed.py` | 数据库种子数据 |
| `app/models/` | SQLAlchemy ORM 模型 |
| `app/crud/` | 数据访问层 |
| `app/services/` | 业务逻辑服务层 |
| `app/schemas/` | Pydantic 请求/响应模型 |
| `app/api/v1/endpoints/` | REST API 路由处理 |

### 前端核心文件
| 文件 | 说明 |
|---|---|
| `frontend/src/main.ts` | Vue 应用入口 |
| `frontend/src/router/index.ts` | 路由配置 + 导航守卫 |
| `frontend/src/api/http.ts` | Axios 实例 + Token 拦截器 |
| `frontend/src/composables/useApprovalSocket.ts` | WebSocket 管理 |
| `frontend/src/composables/useProjectSync.ts` | 跨组件事件总线 |

### 部署核心文件
| 文件 | 说明 |
|---|---|
| `docker-compose.yml` | 11 服务容器编排 |
| `deploy/nginx/dmz.conf` | DMZ 网关 Nginx 配置 |
| `deploy/prometheus/prometheus.yml` | Prometheus 采集配置 |
| `deploy/scripts/deploy.sh` | Linux 部署脚本 |
| `deploy/scripts/deploy.ps1` | Windows 部署脚本 |

---

> **AI Agent 开发原则**：在为本项目生成或修改任何代码时，必须严格遵循以上所有规范。如有不确定的业务逻辑，优先查阅 `app/services/` 和 `app/crud/` 中的已有实现，保持代码风格和架构模式的一致性。所有变更需要经过 `pytest` 验证，关键业务路径需要手动测试确认。
