# 跨模块联调优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在本地运行系统后，验证项目池、派工/修井运行、A5、物料、完井和数据分析报表的闭环一致性，并形成经过复现验证的优化清单。

**Architecture:** 先用后端测试和前端构建建立稳定基线，再以 SQLite 本地种子库运行真实 API 和页面。新增的跨模块测试只负责构造一条业务闭环并断言状态、数量、权限和统计输出；手工联调只验证自动化测试无法覆盖的页面刷新与可视化结果。

**Tech Stack:** FastAPI、SQLAlchemy、pytest、Vue 3、Vite、PowerShell 本地启动脚本。

---

### Task 1: 建立可重复的自动化基线

**Files:**
- Verify: `tests/backend/`
- Verify: `frontend/`
- Verify: `scripts/check-local.ps1`

- [ ] **Step 1: 运行后端全量测试**

```powershell
$env:POSTGRES_PASSWORD='test'
$env:JWT_SECRET_KEY='test-jwt-secret'
$env:DATABASE_URL='sqlite:///./cross_module_baseline.db'
& .\.venv\Scripts\python.exe -m pytest -q
```

Expected: 所有测试通过；记录通过数、失败测试名和首个堆栈。

- [ ] **Step 2: 运行前端生产构建**

```powershell
Push-Location frontend
try { npm run build } finally { Pop-Location }
```

Expected: `vue-tsc --noEmit` 和 Vite 构建成功；记录大于 500 kB 的包体警告但不将其列为阻断问题。

- [ ] **Step 3: 执行已有关键模块测试集**

```powershell
$env:POSTGRES_PASSWORD='test'
$env:JWT_SECRET_KEY='test-jwt-secret'
$env:DATABASE_URL='sqlite:///./cross_module_focus.db'
& .\.venv\Scripts\python.exe -m pytest -q `
  tests/backend/test_a5_sync_service.py `
  tests/backend/test_a5_callback_security.py `
  tests/backend/test_a5_event_workflow.py `
  tests/backend/test_material_external_adapter.py `
  tests/backend/test_material_data_scope.py `
  tests/backend/test_statistics_data_scope.py `
  tests/backend/test_statistics_exports.py `
  tests/backend/test_workover_operation_safety.py
```

Expected: A5、物料、统计权限和运行安全相关测试全部通过。

### Task 2: 增加项目到完井的跨模块自动化闭环测试

**Files:**
- Create: `tests/backend/test_cross_module_closed_loop.py`
- Verify: `app/services/a5_sync_service.py`
- Verify: `app/services/material_external_adapter.py`
- Verify: `app/services/statistics_analysis_service.py`

- [ ] **Step 1: 写入失败的闭环测试**

```python
def test_project_dispatch_a5_material_completion_and_statistics_close_the_same_loop(self):
    project, sheet = self.create_approved_project_and_dispatched_sheet("WELL-CROSS-001", "Unit A")
    a5_result = process_a5_callback_event(
        self.db,
        {"operation_no": sheet.operation_no, "status": "FINISHED", "remark": "closed"},
        event_id="cross-a5-001",
    )
    material = self.create_approved_material(sheet.id, external_material_id="MAT-CROSS-001")
    apply_external_material_event(self.db, self.planned_event("MAT-CROSS-001"))
    self.advance_material_to_used(material.id)
    completion = self.create_completion(sheet.id, "WELL-CROSS-001")
    analysis = build_statistics_analysis(self.db, StatisticsAnalysisQuery(well_no="WELL-CROSS-001"))
    assert a5_result.matched is True
    assert completion.operation_sheet_id == sheet.id
    assert analysis["material_usage"]["used"] == 1
    assert analysis["completion_classification"]["total"] == 1
```

- [ ] **Step 2: 运行测试确认缺失的衔接点**

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/backend/test_cross_module_closed_loop.py -q
```

Expected: 初次运行会暴露状态机、测试夹具或统计关联中的明确失败，不接受跳过或宽松断言。

- [ ] **Step 3: 用最小修复使闭环数据可追溯**

在失败所属模块中保持以下约束：A5 状态更新只匹配 `operation_no`；物料事件只匹配 `external_material_id` 且同一 `event_id` 不重复计量；完井记录必须引用同一 `operation_sheet_id`；统计查询以该运行表关联的项目为唯一事实来源。

- [ ] **Step 4: 重新运行闭环测试**

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/backend/test_cross_module_closed_loop.py -q
```

Expected: 通过，且重复运行不增加物料使用数、完井数或 A5 事件数。

- [ ] **Step 5: 提交闭环测试与最小修复**

```powershell
git add tests/backend/test_cross_module_closed_loop.py app/
git commit -m "test: cover cross-module closed loop"
```

### Task 3: 验证 A5、物料和分析模块的异常及权限边界

**Files:**
- Modify: `tests/backend/test_cross_module_closed_loop.py`
- Verify: `tests/backend/test_a5_callback_security.py`
- Verify: `tests/backend/test_material_data_scope.py`
- Verify: `tests/backend/test_statistics_data_scope.py`

- [ ] **Step 1: 写入重复与未匹配事件断言**

```python
def test_duplicate_or_unknown_external_events_do_not_corrupt_closed_loop_counts(self):
    first = process_a5_callback_event(self.db, self.callback_payload(), event_id="cross-replay-001")
    replay = process_a5_callback_event(self.db, self.callback_payload(), event_id="cross-replay-001")
    unknown = process_a5_callback_event(
        self.db,
        {"operation_no": "UNKNOWN-CROSS", "status": "WORKING"},
        event_id="cross-unknown-001",
    )
    assert first.duplicate is False
    assert replay.duplicate is True
    assert unknown.matched is False
    assert self.integration_event_count("a5") == 2
```

- [ ] **Step 2: 写入上报单位和辖区单位统计断言**

```python
def test_scoped_user_sees_only_its_reporting_or_territory_facts(self):
    scope = DataScope(is_global=False, user_id=7, department="Territory A", reporting_units=("Territory A",))
    result = build_statistics_analysis(self.db, StatisticsAnalysisQuery(), scope=scope)
    assert result["overview_kpis"]["total_projects"] == 1
    assert result["material_usage"]["total"] == 1
    assert result["completion_classification"]["total"] == 1
```

- [ ] **Step 3: 运行异常和权限用例**

```powershell
& .\.venv\Scripts\python.exe -m pytest tests/backend/test_cross_module_closed_loop.py tests/backend/test_a5_callback_security.py tests/backend/test_material_data_scope.py tests/backend/test_statistics_data_scope.py -q
```

Expected: 重放事件不重复处理，未知工单保留待人工复核，非全局用户不获取其他单位明细或聚合值。

- [ ] **Step 4: 提交边界测试与修复**

```powershell
git add tests/backend/test_cross_module_closed_loop.py app/
git commit -m "test: verify integration scope and replay boundaries"
```

### Task 4: 启动本地系统并执行页面级闭环验收

**Files:**
- Verify: `scripts/start-local.ps1`
- Verify: `scripts/check-local.ps1`
- Verify: `frontend/src/views/A5IntegrationView.vue`

- [ ] **Step 1: 启动本地前后端**

```powershell
.\scripts\start-local.ps1
```

Expected: 后端可访问 `http://127.0.0.1:8000/docs`，前端可访问 `http://127.0.0.1:5173`。

- [ ] **Step 2: 检查服务可用性和构建链路**

```powershell
.\scripts\check-local.ps1
```

Expected: Python 编译、单元测试和前端构建完成；若脚本因环境依赖失败，记录实际命令和错误，不修改生产配置绕过失败。

- [ ] **Step 3: 按页面完成闭环操作**

在页面依次完成项目审批、派工、A5 模拟审核、物料模拟同步、物料到场/使用、完井登记，最后打开统计分析和交付汇总页面。每一步记录 URL、操作用户、业务编号、接口响应中的 `code` 与 `data`、页面状态标签和刷新后的统计数字。

- [ ] **Step 4: 导出并核对统计结果**

```powershell
Invoke-WebRequest http://127.0.0.1:8000/openapi.json -OutFile .local\openapi.json
```

Expected: 以 OpenAPI 中的统计和导出接口核对请求参数；Excel、Word 导出的项目数、物料数、完井数与页面筛选结果一致。

### Task 5: 输出问题分级和优化计划

**Files:**
- Create: `docs/验收/2026-07-16-跨模块联调验收记录.md`
- Create: `docs/superpowers/plans/2026-07-16-cross-module-remediation.md`

- [ ] **Step 1: 记录每个场景的证据**

```markdown
| 场景 | 业务编号 | 自动化结果 | 页面结果 | 统计/导出核对 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 项目到完井闭环 | WELL-CROSS-001 | 通过 | 通过 | 一致 | 通过 |
```

- [ ] **Step 2: 按影响分级记录问题**

```markdown
| 级别 | 模块 | 复现步骤 | 实际结果 | 期望结果 | 修复建议 |
| --- | --- | --- | --- | --- | --- |
| P1 | 数据分析 | 以辖区用户导出统计 | 完井数缺失 | 包含辖区项目完井数 | 为完成分类查询传递完整 DataScope |
```

- [ ] **Step 3: 将每个 P0/P1 问题转为修复任务**

修复计划必须为每个问题列出修改文件、先失败后通过的测试命令、回归范围和独立提交信息；P2 问题仅在不影响闭环数据正确性的前提下排序处理。

- [ ] **Step 4: 提交验收记录与修复计划**

```powershell
git add docs/验收/2026-07-16-跨模块联调验收记录.md docs/superpowers/plans/2026-07-16-cross-module-remediation.md
git commit -m "docs: record cross-module integration acceptance"
```
