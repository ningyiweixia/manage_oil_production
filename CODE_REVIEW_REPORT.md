# 代码审查报告 — Manage Factory 系统

**审查日期:** 2026-06-16  
**审查范围:** 全部模块（后端、前端、数据层、部署基础设施）  
**文件总数:** 68+ 文件  
**发现问题总数:** 174 个（40 Critical / 87 Medium / 47 Low）

---

## 总览

| 模块 | 🔴 Critical | 🟡 Medium | 🔵 Low |
|------|-------------|-----------|--------|
| 后端核心（config/security/middleware/redis/ws/deps） | 9 | 14 | 4 |
| 后端 API/CRUD/Service 层 | 6 | 17 | 13 |
| 数据层（models/schemas/alembic） | 6 | 20 | 8 |
| 前端（Vue3/TypeScript） | 10 | 15 | 8 |
| 部署基础设施（Docker/Nginx/Prometheus/Grafana） | 9 | 21 | 14 |
| **合计** | **40** | **87** | **47** |

---

## 🔴 Critical Issues (40)

### 认证与授权

| # | 文件 | 行号 | 问题 | 修复建议 |
|---|------|------|------|----------|
| 1 | `main.py` / `auth.py` | 36 | 登录接口无速率限制，可暴力破解密码 | 使用 `slowapi` 或 Redis 实现 5次/分钟/IP 的限流 |
| 2 | `app/core/config.py` | 21 | 数据库密码默认值 `"postgres"` 是弱密码 | 删除默认值，强制通过环境变量设置 |
| 3 | `app/core/config.py` | 28 | Redis URL 无认证且硬编码本地地址 | 删除默认值或设为 `None`，禁用缓存 |
| 4 | `app/db/seed.py` | 173-175 | 管理员密码 `"ChangeMe_123!"` 硬编码在源码中 | 通过环境变量 `ADMIN_INITIAL_PASSWORD` 读取 |
| 5 | `app/api/ws.py` | 24 | JWT Token 通过 URL 查询参数传递（会被中间日志记录泄露） | 使用 Cookie 或首次 WebSocket 消息传递 Token |
| 6 | `frontend/src/composables/useApprovalSocket.ts` | 17 | 同上，前端 WebSocket Token 在 URL 中 | 同上 |
| 7 | `frontend/src/views/LoginView.vue` | 34 | 默认管理员账号密码硬编码在前端源码 | 删除默认值，仅在 `DEV` 模式下可用 |
| 8 | `frontend/src/views/LoginView.vue` | 52-56 | 网络错误时自动降级为 `demo-token`，绕过认证 | 删除 demo 降级逻辑，显示错误页 |
| 9 | `frontend/src/router/index.ts` | 24 | 路由守卫仅检查 localStorage 中 token 是否存在，不验证有效性 | 添加 Token 过期检查或后端验证 |
| 10 | `frontend/src/api/http.ts` | 11 | Token 存储在 localStorage，XSS 可轻易窃取 | 迁移至 httpOnly Cookie |
| 11 | `README.md` | 100 | 默认管理员凭据在公开文档中 | 替换为占位符说明 |

### 数据完整性与状态机

| # | 文件 | 行号 | 问题 | 修复建议 |
|---|------|------|------|----------|
| 12 | `app/models/approval.py` | 11-20 | 模型定义的 `ApprovalAction` ENUM 有 8 个值，迁移仅创建 4 个，数据库报错 | 创建迁移 0004 补充缺失的 ENUM 值 |
| 13 | `app/models/workover.py` | 135 | `progress` 列无 0-100 CHECK 约束，可插入越界值 | 添加 `CheckConstraint("progress >= 0 AND progress <= 100")` |
| 14 | `app/crud/workover_project_pool.py` | 195-222 | `patch_project_status` 无状态转换验证，可从 DRAFT 直接跳到 APPROVED | 实现状态转移白名单 |
| 15 | `app/api/v1/endpoints/workover_project_pools.py` | 62-84 | 导入 Excel 时每个项目独立 commit，失败时部分数据已写入无法回滚 | 重构为统一事务管理 |
| 16 | `app/api/v1/endpoints/rbac.py` | 67-131 | 分配角色/菜单/权限时，无效 ID 静默忽略 | 验证所有 ID 存在性，不存在时返回错误 |
| 17 | `app/schemas/rbac.py` | 13 | `UserCreate.password` 仅要求 `min_length=8`，接受弱密码 `"aaaaaaaa"` | 添加复杂度校验器（大小写+数字+特殊字符） |
| 18 | `alembic/versions/20260531_0001_init_core_tables.py` | 118 | 同 #12，迁移 ENUM 仅有 4 个值 | 新建迁移补充 |

### 部署安全

| # | 文件 | 行号 | 问题 | 修复建议 |
|---|------|------|------|----------|
| 19 | `docker-compose.yml` | 84 | Redis 无密码认证 | 添加 `--requirepass` 和密码环境变量 |
| 20 | `docker-compose.yml` | 139 | `minio-init` 以 root 运行无安全限制 | 添加 `no-new-privileges` 和 `cap_drop: ALL` |
| 21 | `deploy/nginx/conf.d/dmz.conf` | 60 | CORS 反射 `$http_origin`（完全开放的跨域） | 限制为白名单域名 |
| 22 | `deploy/scripts/deploy.sh` | 22-24 | `docker compose up -d` 后无健康检查等待就执行 exec | 添加健康检查等待循环 |
| 23 | `deploy/scripts/deploy.sh` | 8 | 自动从 `.env.example` 创建 `.env` 并使用弱默认值继续部署 | 强制用户修改密码，否则中止 |
| 24 | `.env` (可能存在) | 3,9,12 | 如果被 Git 追踪，包含真实密码和 JWT 密钥 | 立即轮换所有凭据，`git rm --cached .env` |
| 25 | `requirements.txt` | 8 | `python-jose==3.3.0` 已停止维护（2021年起） | 迁移至 `PyJWT` |
| 26 | `requirements.txt` | 9 | `passlib[bcrypt]==1.7.4` 已弃用 | 直接使用 `bcrypt` |

### 后端核心

| # | 文件 | 行号 | 问题 | 修复建议 |
|---|------|------|------|----------|
| 27 | `app/core/exceptions.py` | 47-48 | 全局异常处理器吞噬所有错误无日志记录 | 添加 `logger.exception()` 记录完整堆栈 |
| 28 | `app/core/redis.py` | 23-28 | Redis 连接失败后永久退化至内存缓存，多 Worker 不一致 | 实现延迟重连或熔断重试机制 |
| 29 | `app/core/middleware.py` | 59-61, 89-90 | 日志写入失败时返回已耗尽的 `body_iterator` | 在 except 中重建 `Response` 对象 |
| 30 | `app/api/ws.py` | 40-43 | `connect()` 在 try 块外，失败时无清理 | 移至 try/finally 内 |

### 前端

| # | 文件 | 行号 | 问题 | 修复建议 |
|---|------|------|------|----------|
| 31 | `frontend/index.html` | 1-12 | 无 Content Security Policy | 添加 CSP meta 标签 |
| 32 | `frontend/src/api/workover.ts` | 8-73 | 硬编码 Demo 数据含逼真井号，可能被误认为真实数据 | 分离为 dev-only fixture，添加明显 Demo 标识 |
| 33 | `frontend/src/views/AnalyticsDashboard.vue` | 229-233 | `exportSummary` 在下载开始前 revoke Object URL，导致下载失败 | 延迟 revoke 或在 click 回调中处理 |
| 34 | `frontend/src/views/AnalyticsDashboard.vue` | 221-224 | 大图表 `getDataURL()` 可能超出浏览器 data URL 限制 | 使用 `canvas.toBlob()` |
| 35 | `frontend/src/composables/useApprovalSocket.ts` | 19 | `JSON.parse()` 无 try/catch，非法消息导致消息处理中断 | 包装 try/catch |
| 36 | `frontend/src/composables/useApprovalSocket.ts` | 34-38 | 无限重连无退避策略 | 实现指数退避+最大重试次数 |

### 其他

| # | 文件 | 行号 | 问题 | 修复建议 |
|---|------|------|------|----------|
| 37 | `app/services/workover_project_pool_excel.py` | 26-33 | Excel 导出存在 Formula Injection 漏洞（CWE-1236） | 所有字符串字段进行公式前缀清洗 |
| 38 | `app/services/workover_project_pool_excel.py` | 16-23 | 无文件大小验证，可上传大文件导致内存耗尽 | 添加 `MAX_UPLOAD_SIZE` 检查（如 10MB） |
| 39 | `app/core/exceptions.py` | 19 | 所有错误返回 HTTP 200，破坏负载均衡和监控的健康检查 | 根据业务码映射到适当的 HTTP 状态码 |
| 40 | `alembic/versions/20260604_0003_system_support_rbac.py` | 29,97 | `ALTER COLUMN method TYPE VARCHAR(16)` 在 `UPPER()` 转换之前执行，可能导致截断 | 先执行 UPDATE 转换数据，再 ALTER 列类型 |

---

## 🟡 Medium Issues (87) — 精选重点

### 安全加固

- **`deploy/nginx/conf.d/dmz.conf`**: CSP 允许 `unsafe-inline`，缺少 TLS 硬化（OCSP Stapling、`ssl_ecdh_curve`），缺少现代安全头（Permissions-Policy, Cross-Origin-*）
- **`deploy/nginx/frontend-site.conf`**: 缺少所有安全头
- **`docker-compose.yml`**: PostgreSQL/MinIO/Grafana 使用弱默认密码，Nginx 拥有过多 `cap_add`（CHOWN/SETUID/SETGID）
- **`app/core/middleware.py`**: 客户端 IP 来自 `request.client.host`（在反向代理后为 127.0.0.1）
- **`app/services/auth_service.py`**: Token 撤销在 Redis 不可用时静默失败
- **`app/api/ws.py`**: Token 过期不重新检查（长连接可能持续数小时）
- **`frontend/src/api/http.ts`**: 无 CSRF 保护

### 数据库与性能

- **FK 索引缺失**: `approval_log.operator_id`, `engineering_design_doc.project_id`, `workover_operation_sheet.project_id`, `workover_project_pool.created_by_id` 缺少索引
- **`app/crud/rbac.py`**: 每次获取用户都 eager load roles+permissions+menus，即使只需要基本属性
- **`app/core/redis.py`**: 无连接池 (`ConnectionPool`)，`socket_connect_timeout=0.2` 过于激进
- **`app/models/dictionary.py`**: `item_label` 唯一性约束缺失
- **`app/models/workover.py`**: `ContractorCapacity` 缺少 `(contractor_name, team_name, report_date)` 唯一约束
- **`app/models/rbac.py`**: `User.email` 无唯一约束，`Menu.children` 未按 `sort_order` 排序
- **`alembic/env.py`**: `compare_type=True` 可能生成导致锁表的重写迁移

### API 设计

- **`app/api/v1/endpoints/auth.py`**: Refresh Token 不轮换（安全风险），登出要求有效 Refresh Token（已过期的 Token 无法登出）
- **`app/api/v1/endpoints/dictionaries.py`**: 列表接口无分页
- **`app/api/v1/endpoints/rbac.py`**: 删除用户是软删除但使用 HTTP DELETE，与其他实体的硬删除不一致
- **`app/api/v1/endpoints/rbac.py`**: 操作日志无分页，硬编码 limit=100
- **`app/schemas/rbac.py`**: 所有 Update Schema 继承 Create Schema，不支持部分更新
- **`app/schemas/auth.py`**: `LoginResponse` 数据重复（顶层和 user 嵌套层均有相同数据）

### 事务完整性

- **`app/crud/dictionary.py` / `app/crud/rbac.py`**: CRUD 函数内部调用 `db.commit()`，阻止上层组合多个操作的事务
- **`app/crud/workover_project_pool.py`**: `write_approval_log` 仅 `db.add()` 无 `db.flush()`，审计日志依赖调用者 commit
- **`app/services/audit_service.py`**: 同上，`add` 后未 `flush`，`log.id` 对调用者不可用

### 前端

- **`src/views/MainLayout.vue`**: `computed` 读取 localStorage 无响应式依赖，数据不会更新
- **`src/views/ApprovalWorkbench.vue`**: `selectedIds` 在数据刷新后不清除，保留过期 ID
- **`src/views/AnalyticsDashboard.vue`**: 筛选器每次按键触发 `router.replace()`，应加去抖
- **`src/router/index.ts`**: 登录后未保存目标路径，始终跳转 `/approval`
- **`src/composables/useApprovalSocket.ts`**: 多次 `connect()` 调用导致 WebSocket 泄漏
- **`src/types/workover.ts`**: `status?: ProjectPoolStatus | ''` 空字符串为前端特化 sentinel
- **`src/styles/main.css`**: 登录背景依赖外部 Unsplash URL（隐私/可用性风险）
- **`vite.config.ts`**: 代理目标 `http://127.0.0.1:8000` 硬编码

### 监控与告警

- **`deploy/prometheus/prometheus.yml`**: Nginx job 抓取 `/healthz` 而非 metrics 端点
- **`deploy/prometheus/rules/manage_factory_alerts.yml`**: 缺少 PostgreSQL 宕机、Redis 宕机、5xx 错误率告警
- **`deploy/prometheus/prometheus.yml`**: 无 Alertmanager 配置

### 部署脚本

- **`deploy/scripts/deploy.sh`**: 自签名证书 10 年有效期过长，缺少 openssl/docker 前置检查
- **`deploy/scripts/deploy.sh`**: `set -u` 但无 `set -o pipefail`
- **`deploy/README.md`**: 引用的 `deploy.ps1` 不存在

---

## 🔵 Low Issues (47) — 精选重点

- **`app/core/middleware.py`**: `json.loads(body.decode("utf-8"))` 未处理解码错误
- **`app/core/middleware.py`**: `username` 在操作日志中硬编码为 `None`
- **`app/core/middleware.py`**: 响应体缓冲用于日志记录使内存加倍
- **`app/services/notification_service.py`**: `well_nos` 为空时通知消息出现前导空格
- **`app/services/dictionary_service.py`**: 错误消息泄露内部字典类型名称
- **`app/services/auth_service.py`**: Token 撤销最小 TTL 为 1 秒
- **`app/models/dictionary.py`**: `func.now()` 返回事务时间戳非墙钟时间
- **`app/db/session.py`**: 未配置 `pool_size`/`max_overflow`
- **`app/api/v1/endpoints/dictionaries.py`**: `is_active` 作为查询参数而非请求体
- **`app/schemas/workover_project_pool.py`**: `Decimal` 类型在 JSONB 中序列化可能失败
- **`frontend/src/utils/status.ts`**: `statusStep` 与 `el-steps` 之间为隐式契约
- **`frontend/src/main.ts`**: Element Plus CSS 全局导入未 tree-shake
- **`alembic.ini`**: 包含占位符 `sqlalchemy.url`
- **`requirements.txt`**: 无哈希锁定、无开发/生产依赖分离、缺少文档中引用的依赖（celery 等）
- **`.gitignore`**: 缺少 `.vscode/`, `.idea/`, `.DS_Store`, `Thumbs.db` 等

---

## 修复优先级建议

### 第一优先（立即修复）— 安全漏洞

1. **认证绕过**: 删除前端 Demo 降级逻辑、硬编码凭据
2. **Token 泄露**: JWT 从 URL 查询参数移至 Cookie 或消息体
3. **无速率限制**: 登录接口添加 IP 级别限流
4. **CORS 完全开放**: 限制为白名单
5. **Redis 无密码**: 添加 `requirepass`
6. **python-jose/passlib 弃用**: 迁移至 PyJWT/bcrypt
7. **.env 泄露**: 确认未在 Git 中追踪

### 第二优先（本周内修复）— 数据完整性与可靠性

1. **ENUM 不一致**: 创建迁移修复 ApprovalAction
2. **状态机验证**: 实现状态转移白名单
3. **事务管理**: Excel 导入、CRUD commit 重构
4. **进度列约束**: 添加 CHECK 约束
5. **弱密码策略**: 添加复杂度校验
6. **日志/异常处理**: 全局异常日志、响应体重构

### 第三优先（本迭代修复）— 代码质量与性能

1. **FK 索引**: 添加缺失索引
2. **分页**: 字典列表、操作日志
3. **Eager Load 优化**: 按需加载 RBAC 关系
4. **Redis 连接池**: 使用 ConnectionPool
5. **Update Schema**: 支持部分更新
6. **安全头**: Nginx 添加完整安全头
7. **告警规则**: 补充 PostgreSQL/Redis/5xx 告警
8. **CSP**: 前端添加 Content Security Policy
