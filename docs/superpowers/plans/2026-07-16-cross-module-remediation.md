# 跨模块页面与导出复测 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补齐跨模块链路的浏览器页面操作和 Excel/Word 导出文件验收证据，关闭 P1 发布验收缺口。

**Architecture:** 不改变既有业务实现。使用当前本地 mock 数据库启动 FastAPI 与 Vite，在浏览器中以具备权限的测试用户完成项目、派工、A5、物料、完井、分析与导出核验；将请求响应、页面刷新后的数值和导出文件内容写回验收记录。

**Tech Stack:** FastAPI、Vue 3、Vite、Playwright Chromium、PowerShell、pytest。

---

### Task 1: 准备可重复的浏览器验收运行环境

**Files:**
- Verify: `AGENTS.md`
- Verify: `main.py`
- Verify: `frontend/vite.config.ts`
- Verify: `frontend/package.json`
- Update evidence: `docs/验收/2026-07-16-跨模块联调验收记录.md`

- [ ] **Step 1: 安装并验证 Playwright Chromium**

```powershell
Push-Location frontend
try {
  npx playwright install chromium
  npx playwright --version
} finally { Pop-Location }
```

Expected: 安装命令在联网可用的环境完成，并输出 Playwright 版本；若仍超时，记录完整错误、网络条件和重试时间，不修改业务代码。

- [ ] **Step 2: 预检端口并初始化隔离的 SQLite/mock 数据库**

```powershell
$repoRoot = (Resolve-Path .).Path
$python = (Resolve-Path (Join-Path $repoRoot '..\..\.venv\Scripts\python.exe')).Path
$ports = 8001, 5174
$inUse = Get-NetTCPConnection -State Listen -LocalPort $ports -ErrorAction SilentlyContinue
if ($inUse) { throw "Refusing to reuse occupied acceptance ports: $($inUse.LocalPort -join ', ')" }

$env:DATABASE_URL = 'sqlite:///./.local/cross_module_browser.db'
$env:POSTGRES_PASSWORD = 'test'
$env:JWT_SECRET_KEY = 'test-jwt-secret'
$env:ADMIN_INITIAL_PASSWORD = 'ChangeMe_123!'
$env:A5_ADAPTER_MODE = 'mock'
$env:MATERIAL_ADAPTER_MODE = 'mock'
$env:CORS_ALLOW_ORIGINS = 'http://127.0.0.1:5174'
$env:REDIS_URL = ''

@'
from app.db.base import Base
from app.db.seed import seed
from app.db.session import engine

Base.metadata.create_all(bind=engine)
seed()
print('Cross-module browser database initialized')
'@ | & $python -
```

Expected: 端口 8001 与 5174 在启动前未被其他服务占用；数据库只写入工作树的 `.local/cross_module_browser.db`，并启用 A5、物料 mock。

- [ ] **Step 3: 启动隔离的后端和前端进程**

```powershell
$repoRoot = (Resolve-Path .).Path
$python = (Resolve-Path (Join-Path $repoRoot '..\..\.venv\Scripts\python.exe')).Path
$backendScript = @'
Set-Location '__REPO_ROOT__'
$env:DATABASE_URL = 'sqlite:///./.local/cross_module_browser.db'
$env:POSTGRES_PASSWORD = 'test'
$env:JWT_SECRET_KEY = 'test-jwt-secret'
$env:ADMIN_INITIAL_PASSWORD = 'ChangeMe_123!'
$env:A5_ADAPTER_MODE = 'mock'
$env:MATERIAL_ADAPTER_MODE = 'mock'
$env:CORS_ALLOW_ORIGINS = 'http://127.0.0.1:5174'
$env:REDIS_URL = ''
& '__PYTHON__' -m uvicorn main:app --host 127.0.0.1 --port 8001
'@.Replace('__REPO_ROOT__', $repoRoot).Replace('__PYTHON__', $python)
$frontendScript = @'
Set-Location '__FRONTEND_ROOT__'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8001/api/v1'
$env:VITE_WS_BASE_URL = 'ws://127.0.0.1:8001/ws/approval'
& npm.cmd run dev -- --host 127.0.0.1 --port 5174
'@.Replace('__FRONTEND_ROOT__', (Join-Path $repoRoot 'frontend'))

$backendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($backendScript))
$frontendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($frontendScript))
cmd.exe /c ('start "cross-module-backend" /min powershell.exe -NoProfile -EncodedCommand {0}' -f $backendEncoded)
cmd.exe /c ('start "cross-module-frontend" /min powershell.exe -NoProfile -EncodedCommand {0}' -f $frontendEncoded)
```

Expected: 后端在 `http://127.0.0.1:8001/docs` 提供服务；前端在 `http://127.0.0.1:5174` 提供服务，并通过 `VITE_API_BASE_URL` 与 `VITE_WS_BASE_URL` 指向同一套后端。命令不依赖任何未跟踪的 `.local/*.ps1` 文件。

- [ ] **Step 4: 记录可用性证据**

```powershell
$deadline = (Get-Date).AddSeconds(30)
do {
  try { $backend = Invoke-WebRequest -Uri http://127.0.0.1:8001/health -UseBasicParsing -TimeoutSec 2 } catch { $backend = $null }
  try { $frontend = Invoke-WebRequest -Uri http://127.0.0.1:5174 -UseBasicParsing -TimeoutSec 2 } catch { $frontend = $null }
  if ($backend -and $frontend) { break }
  Start-Sleep -Seconds 1
} while ((Get-Date) -lt $deadline)
if (-not $backend -or -not $frontend) { throw 'Acceptance services did not become ready within 30 seconds' }
```

Expected: 两个 HTTP 请求均成功后，记录执行时间、端口与状态到验收记录；继续保持进程运行以完成任务 2 和任务 3。

- [ ] **Step 5: 提交验收环境证据（仅当记录有变化）**

```powershell
git add docs/验收/2026-07-16-跨模块联调验收记录.md
git commit -m "docs: record browser acceptance environment"
```

### Task 2: 复测页面闭环与统计刷新

**Files:**
- Verify: `frontend/src/views/A5IntegrationView.vue`
- Verify: `frontend/src/views/MaterialManagementView.vue`
- Verify: `frontend/src/views/StatisticsAnalysisView.vue`
- Verify: `tests/backend/test_cross_module_closed_loop.py`
- Update evidence: `docs/验收/2026-07-16-跨模块联调验收记录.md`

- [ ] **Step 1: 先运行现有闭环回归作为页面数据基线**

```powershell
$env:POSTGRES_PASSWORD='test'
$env:JWT_SECRET_KEY='test-jwt-secret'
$env:DATABASE_URL='sqlite:///./cross_module_ui_rerun.db'
& 'D:\workspace\githubprojects\oil_production\manage_oil_production\.venv\Scripts\python.exe' -m pytest -q tests/backend/test_cross_module_closed_loop.py
```

Expected: 测试通过，确认页面验收对应的项目、工单、A5、物料和完井状态机仍受自动化覆盖。

- [ ] **Step 2: 用 Playwright 依次执行并截图下列页面状态**

```text
登录 → 项目池审批/派工 → 修井运行工单 → A5 mock 状态 → 物料计划、到货与使用 → 完井登记 → 数据分析
```

Expected: 每一步 URL、操作用户、业务编号、接口 `code=20000`、页面状态标签和刷新后的统计值均被记录；A5 页面显示 mock 模式；数据分析的项目、工单、物料、完井和追溯来源与 API 基线一致。

- [ ] **Step 3: 对页面结果执行接口交叉核对**

```powershell
Invoke-WebRequest http://127.0.0.1:8000/openapi.json -OutFile .local\openapi.json
```

Expected: 从 OpenAPI 确认页面调用的统计与导出接口，再以相同筛选条件请求接口；页面数字与接口响应逐项一致。

- [ ] **Step 4: 提交页面验收证据（仅当记录有变化）**

```powershell
git add docs/验收/2026-07-16-跨模块联调验收记录.md
git commit -m "docs: record cross-module browser acceptance"
```

### Task 3: 核验 Excel 与 Word 导出文件并关闭 P1

**Files:**
- Verify: `app/api/v1/endpoints/reports.py`
- Verify: `app/services/report_service.py`
- Verify: `tests/backend/test_statistics_exports.py`
- Update evidence: `docs/验收/2026-07-16-跨模块联调验收记录.md`

- [ ] **Step 1: 运行导出回归测试**

```powershell
$env:POSTGRES_PASSWORD='test'
$env:JWT_SECRET_KEY='test-jwt-secret'
$env:DATABASE_URL='sqlite:///./cross_module_export_rerun.db'
& 'D:\workspace\githubprojects\oil_production\manage_oil_production\.venv\Scripts\python.exe' -m pytest -q tests/backend/test_statistics_exports.py
```

Expected: 导出测试通过；若失败，保留失败用例、首个堆栈和生成文件作为缺陷证据，再创建单独修复计划，不在本任务中臆测代码改动。

- [ ] **Step 2: 从页面分别下载 Excel 和 Word，并检查文件内容**

```text
在与数据分析页面相同的筛选条件下，分别触发 Excel 与 Word 导出；核对项目数、物料数、完井数和筛选条件与页面/API 的数值一致。
```

Expected: 两个文件可打开，字段完整，且四类汇总数据与同条件页面/API 完全一致；记录文件名、大小、下载时间和核对数值。

- [ ] **Step 3: 停止本次验收启动的后台进程**

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8001,5174 -ErrorAction SilentlyContinue |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object { Stop-Process -Id $_ -Force }
```

Expected: 仅停止任务 2 已验证为空闲、任务 3 在 8001/5174 上创建的本次验收进程；若浏览器或导出验证提前失败，也必须先执行此命令再记录失败证据。

- [ ] **Step 4: 更新结论并关闭 P1（仅在全部证据成立时）**

```markdown
将 P1 状态更新为“已关闭”，并保留 Playwright 安装、页面操作和两种导出文件的证据；若任一环节未完成，P1 保持开启。
```

Expected: 验收记录的结论与实际证据一致，不把未执行项标记为通过。

- [ ] **Step 5: 提交最终验收记录（仅当记录有变化）**

```powershell
git add docs/验收/2026-07-16-跨模块联调验收记录.md
git commit -m "docs: close cross-module acceptance gap"
```
