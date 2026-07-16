# A5、物料与数据分析闭环加固实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不依赖真实外部系统的前提下，修复 A5 回调安全和数据越权风险，并为 A5、物料及统计模块提供可重复的模拟接口和统一验收数据。

**Architecture:** 将 A5 和物料外部交互限定在可注入的适配器层；领域服务继续拥有状态机和数量校验。API 在入口生成 `DataScope`，所有明细、统计和导出都携带该范围。A5 事件持久化后以事件键实现幂等、重放保护和人工复核。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy 2、Pydantic v2、Alembic、httpx、SQLite 测试数据库、Vue 3、TypeScript、pytest。

---

## 文件职责

- `app/core/config.py`：声明适配器模式、回调时间窗和生产环境配置约束。
- `app/models/integration.py`：保存 A5 回调和物料外部事件的可审计处理状态。
- `app/services/a5_auth_service.py`：规范化头部并校验 HMAC、时间戳和来源。
- `app/services/a5_adapter.py`：定义 A5 协议，提供 HTTP 与确定性 mock 实现。
- `app/services/material_external_adapter.py`：定义物料外部协议，提供 HTTP 与确定性 mock 实现。
- `app/services/data_scope_service.py`：生成稳定的数据范围及 SQL 谓词。
- `app/services/statistics_analysis_service.py`、`app/services/report_service.py`：在相同范围和查询下聚合、缓存、导出。
- `app/api/v1/endpoints/*.py`：把当前用户范围传给领域服务，并返回统一的无权资源结果。
- `tests/backend/test_*`：以临时 SQLite 数据库和 httpx mock transport 验证每个边界。

### Task 1: 建立 A5 回调安全回归测试

**Files:**
- Create: `tests/backend/test_a5_callback_security.py`
- Modify: `app/services/a5_auth_service.py`

- [ ] **Step 1: 写入失败测试，覆盖小写请求头和密钥缺失拒绝。**

```python
def signed_headers(body: str, secret: str, timestamp: int) -> dict[str, str]:
    signature = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()
    return {"x-a5-signature": signature, "x-a5-timestamp": str(timestamp)}

def test_lowercase_asgi_header_with_valid_hmac_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "a5_api_secret", "test-secret")
    body = '{"operation_no":"OP-1"}'
    assert verify_a5_callback_signature(signed_headers(body, "test-secret", now_timestamp()), body)

def test_missing_secret_is_rejected_in_every_environment(monkeypatch):
    monkeypatch.setattr(settings, "a5_api_secret", "")
    assert not verify_a5_callback_signature({"x-a5-signature": "anything"}, "{}")
```

- [ ] **Step 2: 运行测试，确认当前实现失败。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_callback_security.py -q`

Expected: 小写头部用例失败，且缺失密钥用例显示当前宽松行为。

- [ ] **Step 3: 最小化实现规范化和失败关闭。**

```python
def _normalized_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(key).lower(): value for key, value in headers.items()}

def verify_a5_callback_signature(headers: Mapping[str, str], body: str = "") -> bool:
    normalized = _normalized_headers(headers)
    secret = settings.a5_api_secret
    if not secret:
        logger.error("A5 callback secret is not configured")
        return False
    signature = normalized.get("x-a5-signature", "")
    timestamp = normalized.get("x-a5-timestamp", "")
    # 验证 timestamp、HMAC(timestamp.body) 和来源 IP。
```

保留 `hmac.compare_digest`，时间偏差超过 `settings.a5_callback_max_skew_seconds`（默认 300）即拒绝。更新 `app/core/config.py`，增加该配置字段。

- [ ] **Step 4: 重新运行安全测试和原 A5 测试。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_callback_security.py tests/backend/test_a5_sync_service.py -q`

Expected: PASS。

- [ ] **Step 5: 提交此独立修复。**

```powershell
git add app/core/config.py app/services/a5_auth_service.py tests/backend/test_a5_callback_security.py
git commit -m "fix: harden A5 callback signature verification"
```

### Task 2: 持久化 A5 事件并实现重放保护

**Files:**
- Create: `app/models/integration.py`
- Modify: `app/models/__init__.py`
- Create: `alembic/versions/20260716_0016_integration_events.py`
- Modify: `app/services/a5_sync_service.py`
- Modify: `app/api/v1/endpoints/a5_integration.py`
- Create: `tests/backend/test_a5_event_workflow.py`

- [ ] **Step 1: 写入失败测试，定义事件键、重复与冲突行为。**

```python
def test_same_event_id_and_payload_updates_operation_once(client, signed_callback):
    first = client.post("/api/v1/a5/callback", content=signed_callback("evt-1", "WORKING"))
    second = client.post("/api/v1/a5/callback", content=signed_callback("evt-1", "WORKING"))
    assert first.status_code == second.status_code == 200
    assert integration_event_count("evt-1") == 1

def test_same_event_id_with_different_payload_returns_conflict(client, signed_callback):
    client.post("/api/v1/a5/callback", content=signed_callback("evt-2", "WORKING"))
    response = client.post("/api/v1/a5/callback", content=signed_callback("evt-2", "FINISHED"))
    assert response.status_code == 409
```

测试还应验证无事件 ID 时从规范化 JSON 生成稳定 SHA-256 键，未知工单进入 `PENDING_REVIEW`。

- [ ] **Step 2: 运行测试，确认事件表和幂等流程不存在。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_event_workflow.py -q`

Expected: FAIL，原因是模型、迁移或事件服务不存在。

- [ ] **Step 3: 新增 `IntegrationEvent` 模型、迁移和处理服务。**

```python
class IntegrationEventStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PROCESSED = "PROCESSED"
    PENDING_REVIEW = "PENDING_REVIEW"
    FAILED = "FAILED"

class IntegrationEvent(Base, TimestampMixin):
    __tablename__ = "integration_event"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    event_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[IntegrationEventStatus] = mapped_column(...)
    operation_no: Mapped[str | None] = mapped_column(String(64), index=True)
```

在同一数据库事务中先插入事件，再调用 `apply_a5_update_to_operation_sheet`。唯一键冲突时比较 `payload_hash`：相同则返回已有事件结果，不同则抛出业务冲突。未知工单不更新作业，保存为 `PENDING_REVIEW`。

- [ ] **Step 4: 运行事件工作流和数据库迁移测试。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_event_workflow.py tests/backend/test_database_unavailable.py -q`

Expected: PASS。

- [ ] **Step 5: 提交事件处理闭环。**

```powershell
git add app/models/integration.py app/models/__init__.py alembic/versions/20260716_0016_integration_events.py app/services/a5_sync_service.py app/api/v1/endpoints/a5_integration.py tests/backend/test_a5_event_workflow.py
git commit -m "feat: persist idempotent A5 callback events"
```

### Task 3: 为物料和统计统一注入数据范围

**Files:**
- Modify: `app/services/data_scope_service.py`
- Modify: `app/crud/material.py`
- Modify: `app/api/v1/endpoints/materials.py`
- Modify: `app/services/statistics_analysis_service.py`
- Modify: `app/services/report_service.py`
- Modify: `app/api/v1/endpoints/reports.py`
- Create: `tests/backend/test_material_and_reports_data_scope.py`

- [ ] **Step 1: 写入失败测试，证明跨单位数据不能读取或聚合。**

```python
def test_user_cannot_read_other_reporting_unit_material(client, unit_a_headers, material_in_unit_b):
    response = client.get(f"/api/v1/materials/{material_in_unit_b.id}", headers=unit_a_headers)
    assert response.status_code == 404

def test_statistics_and_export_exclude_other_reporting_unit(db, unit_a_user):
    scope = build_data_scope(unit_a_user)
    result = build_statistics_analysis(db, StatisticsAnalysisQuery(), scope)
    assert result["material_usage"]["total"] == 1
```

测试覆盖列表、详情、更新、删除、物料汇总、统计 JSON、Excel 和 Word；管理员用例应保留全局可见性。

- [ ] **Step 2: 运行测试，确认当前服务不接收范围参数。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_material_and_reports_data_scope.py -q`

Expected: FAIL，原因是越权记录可见或函数签名缺少 `scope`。

- [ ] **Step 3: 实现不可变 `DataScope` 和 SQL 级谓词。**

```python
class DataScope(BaseModel):
    is_global: bool
    user_id: int
    department: str | None = None
    reporting_units: tuple[str, ...] = ()

def material_scope_predicate(scope: DataScope):
    if scope.is_global:
        return true()
    return WorkoverProjectPool.report_unit.in_(scope.reporting_units)
```

让 `list_material_requirements`、`get_material_requirement`、`create_material_requirement`、`update_material_requirement`、`delete_material_requirement` 和 `get_material_analytics` 全部接收 `scope`。范围外详情通过与范围合并的 SQL 查询返回不存在。报告端点获得 `current_user` 后，向统计与导出传递同一 `scope`。

- [ ] **Step 4: 将范围摘要纳入统计缓存键并运行聚焦测试。**

```python
cache_key = hashlib.sha256(
    json.dumps({"query": query.model_dump(mode="json"), "scope": scope.model_dump(mode="json")}, sort_keys=True).encode()
).hexdigest()
```

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_material_and_reports_data_scope.py tests/backend/test_material_closed_loop_contract.py tests/backend/test_statistics_analysis_filters.py tests/backend/test_statistics_exports.py -q`

Expected: PASS。

- [ ] **Step 5: 提交权限与统计范围改造。**

```powershell
git add app/services/data_scope_service.py app/crud/material.py app/api/v1/endpoints/materials.py app/services/statistics_analysis_service.py app/services/report_service.py app/api/v1/endpoints/reports.py tests/backend/test_material_and_reports_data_scope.py
git commit -m "fix: apply data scope to material and reports"
```

### Task 4: 提供 A5 可替换适配器和确定性模拟场景

**Files:**
- Create: `app/services/a5_adapter.py`
- Modify: `app/core/config.py`
- Modify: `app/services/a5_sync_service.py`
- Modify: `app/services/a5_client.py`
- Create: `tests/backend/test_a5_adapter.py`

- [ ] **Step 1: 写入失败测试，定义 adapter mode 与五种模拟结果。**

```python
async def test_mock_a5_adapter_returns_repeatable_daily_anomaly_and_process_records():
    adapter = MockA5Adapter(scenario="normal")
    assert await adapter.fetch_daily_reports(date(2026, 7, 16)) == await adapter.fetch_daily_reports(date(2026, 7, 16))
    assert len(await adapter.fetch_anomalies(date(2026, 7, 16))) == 1
    assert len(await adapter.fetch_process_progress(date(2026, 7, 16))) == 1

async def test_mock_a5_timeout_scenario_raises_external_timeout():
    with pytest.raises(ExternalIntegrationError, match="TIMEOUT"):
        await MockA5Adapter(scenario="timeout").fetch_daily_reports(date(2026, 7, 16))
```

- [ ] **Step 2: 运行测试，确认适配器模块不存在。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_adapter.py -q`

Expected: FAIL，原因是 `a5_adapter` 模块不存在。

- [ ] **Step 3: 定义协议、HTTP 实现和 mock 实现。**

```python
class A5Adapter(Protocol):
    async def fetch_daily_reports(self, report_date: date) -> list[dict[str, Any]]: ...
    async def fetch_anomalies(self, report_date: date) -> list[dict[str, Any]]: ...
    async def fetch_process_progress(self, report_date: date) -> list[dict[str, Any]]: ...

def get_a5_adapter() -> A5Adapter:
    if settings.a5_adapter_mode == "mock":
        return MockA5Adapter(settings.a5_mock_scenario)
    return HttpA5Adapter(A5Client())
```

`normal` 场景返回固定的日报、异常和工序；`empty` 返回空列表；`timeout` 抛出分类错误；`error` 抛出远程错误；`duplicate` 返回重复事件。`http` 模式在 `prod` 缺少地址、密钥或 API key 时抛出配置错误，不得回退至 mock。

- [ ] **Step 4: 改造同步服务只依赖适配器，并运行回归。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_adapter.py tests/backend/test_a5_sync_service.py -q`

Expected: PASS。

- [ ] **Step 5: 提交 A5 模拟接口。**

```powershell
git add app/services/a5_adapter.py app/core/config.py app/services/a5_sync_service.py app/services/a5_client.py tests/backend/test_a5_adapter.py
git commit -m "feat: add deterministic A5 adapter modes"
```

### Task 5: 提供物料外部适配器并保护状态机

**Files:**
- Create: `app/services/material_external_adapter.py`
- Modify: `app/core/config.py`
- Modify: `app/crud/material.py`
- Modify: `app/api/v1/endpoints/materials.py`
- Create: `tests/backend/test_material_external_adapter.py`

- [ ] **Step 1: 写入失败测试，定义 mock 物料事件与幂等处理。**

```python
async def test_mock_material_events_drive_only_legal_transitions(db, requirement):
    adapter = MockMaterialExternalAdapter(scenario="normal")
    events = await adapter.fetch_events(datetime(2026, 7, 16, tzinfo=UTC))
    apply_external_material_event(db, events[0])
    assert requirement.status is MaterialRequirementStatus.PLANNED

def test_duplicate_material_event_does_not_increment_quantity_twice(db, delivered_requirement):
    event = MaterialExternalEvent(event_id="mat-evt-1", status="ARRIVED", quantity=5)
    apply_external_material_event(db, event)
    apply_external_material_event(db, event)
    assert delivered_requirement.arrived_quantity == 5
```

- [ ] **Step 2: 运行测试，确认物料适配器不存在。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_material_external_adapter.py -q`

Expected: FAIL，原因是适配器和事件应用服务不存在。

- [ ] **Step 3: 实现协议、模式选择和受控事件应用。**

```python
class MaterialExternalAdapter(Protocol):
    async def submit_plan(self, request: MaterialPlanRequest) -> MaterialPlanResult: ...
    async def fetch_events(self, since: datetime) -> list[MaterialExternalEvent]: ...

def apply_external_material_event(db: Session, event: MaterialExternalEvent, scope: DataScope) -> MaterialRequirement:
    requirement = get_material_requirement_by_external_id(db, event.external_material_id, scope)
    return update_material_requirement(db, requirement.id, MaterialRequirementUpdate(...), scope=scope)
```

使用 `IntegrationEvent(source="material")` 的唯一 `event_key` 保护重复事件。事件映射仅能推进 `PENDING -> APPROVED -> PLANNED -> DELIVERED -> ARRIVED -> USED` 或取消，不允许直接写状态与数量字段。超时、远端错误和数量不合法必须保留原记录并标记事件失败。

- [ ] **Step 4: 运行物料适配器、状态机和数据范围测试。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_material_external_adapter.py tests/backend/test_material_closed_loop_contract.py tests/backend/test_material_and_reports_data_scope.py -q`

Expected: PASS。

- [ ] **Step 5: 提交物料虚拟接口。**

```powershell
git add app/services/material_external_adapter.py app/core/config.py app/crud/material.py app/api/v1/endpoints/materials.py tests/backend/test_material_external_adapter.py
git commit -m "feat: add mockable material external adapter"
```

### Task 6: 统一统计事实、导出与前端集成状态

**Files:**
- Modify: `app/services/statistics_analysis_service.py`
- Modify: `app/services/report_service.py`
- Modify: `app/schemas/analytics.py`
- Modify: `frontend/src/api/a5.ts`
- Modify: `frontend/src/api/material.ts`
- Modify: `frontend/src/views/A5IntegrationView.vue`
- Modify: `frontend/src/views/MaterialManageView.vue`
- Modify: `frontend/src/views/AnalyticsDashboard.vue`
- Create: `tests/backend/test_closed_loop_statistics_consistency.py`
- Create: `tests/backend/test_frontend_integration_modes_contract.py`

- [ ] **Step 1: 写入失败测试，要求看板、明细和导出共享统计事实。**

```python
def test_dashboard_drilldown_excel_and_word_share_scoped_totals(db, unit_a_scope):
    result = build_statistics_analysis(db, StatisticsAnalysisQuery(), unit_a_scope)
    rows = build_statistics_drilldown(db, "material_requirements", StatisticsAnalysisQuery(), unit_a_scope)
    excel = export_statistics_analysis_excel(db, StatisticsAnalysisQuery(), unit_a_scope)
    assert result["material_usage"]["total"] == rows["total"] == read_excel_total(excel, "物料需求总数")

def test_frontend_shows_adapter_mode_and_external_failure_state():
    source = Path("frontend/src/views/A5IntegrationView.vue").read_text(encoding="utf-8")
    assert "adapter_mode" in source and "模拟接口" in source and "正式接口" in source
```

- [ ] **Step 2: 运行测试，确认范围参数或显示字段缺失。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_closed_loop_statistics_consistency.py tests/backend/test_frontend_integration_modes_contract.py -q`

Expected: FAIL，原因是 A5/物料集成状态尚未纳入统一结果，前端没有模式状态。

- [ ] **Step 3: 在统计结果中增加集成状态，并让导出复用结果。**

```python
integration_status = {
    "a5_adapter_mode": settings.a5_adapter_mode,
    "a5_processed": count_events(db, "a5", "PROCESSED", scope),
    "a5_pending_review": count_events(db, "a5", "PENDING_REVIEW", scope),
    "material_adapter_mode": settings.material_adapter_mode,
}
return {**existing_result, "integration_status": integration_status}
```

导出函数必须接收 `query` 和 `scope` 并调用一次 `build_statistics_analysis`。前端从 API 响应展示适配器模式、最近错误和待复核数；错误状态不得被显示为零数据。

- [ ] **Step 4: 运行统计、前端契约和生产构建。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_closed_loop_statistics_consistency.py tests/backend/test_frontend_integration_modes_contract.py tests/backend/test_statistics_analysis_contract.py tests/backend/test_statistics_exports.py -q`

Run: `npm run build`（工作目录：`frontend`）

Expected: pytest PASS；TypeScript 检查和 Vite 构建成功。

- [ ] **Step 5: 提交统计与界面状态改造。**

```powershell
git add app/services/statistics_analysis_service.py app/services/report_service.py app/schemas/analytics.py frontend/src/api/a5.ts frontend/src/api/material.ts frontend/src/views/A5IntegrationView.vue frontend/src/views/MaterialManageView.vue frontend/src/views/AnalyticsDashboard.vue tests/backend/test_closed_loop_statistics_consistency.py tests/backend/test_frontend_integration_modes_contract.py
git commit -m "feat: expose scoped integration status in analytics"
```

### Task 7: 完成迁移、端到端验收与运行文档

**Files:**
- Modify: `README.md`
- Create: `docs/验收/A5物料统计模拟接口验收记录.md`
- Modify: `tests/backend/test_phase1_demo_readiness.py`
- Create: `tests/backend/test_mock_integration_acceptance.py`

- [ ] **Step 1: 写入失败验收测试，组合 A5、物料和统计固定场景。**

```python
def test_mock_mode_closed_loop_acceptance(client, scoped_user_headers):
    trigger = client.post("/api/v1/a5/sync/trigger", headers=scoped_user_headers)
    assert trigger.status_code == 200
    material = client.post("/api/v1/materials/external/sync", headers=scoped_user_headers)
    assert material.status_code == 200
    statistics = client.get("/api/v1/reports/statistics-analysis", headers=scoped_user_headers).json()["data"]
    assert statistics["integration_status"]["a5_adapter_mode"] == "mock"
    assert statistics["material_usage"]["total"] >= 1
```

- [ ] **Step 2: 运行验收测试，确认全部链路在 mock 模式可用。**

Run: `.venv\Scripts\python.exe -m pytest tests/backend/test_mock_integration_acceptance.py -q`

Expected: PASS。

- [ ] **Step 3: 执行一次性迁移往返验证。**

Run: `.venv\Scripts\alembic.exe upgrade head`

Run: `.venv\Scripts\alembic.exe downgrade -1`

Run: `.venv\Scripts\alembic.exe upgrade head`

Expected: 三条命令成功，`integration_event` 表创建、回退并重建。

- [ ] **Step 4: 更新启动、配置与真实接口切换文档。**

README 必须记录 `A5_ADAPTER_MODE`、`A5_API_SECRET`、`A5_CALLBACK_MAX_SKEW_SECONDS`、`MATERIAL_ADAPTER_MODE`，说明本地 `mock` 默认值、生产 `http` 必需配置、回滚方式和回调密钥轮换步骤。验收记录写入固定模拟场景、执行命令、实际结果和已知限制。

- [ ] **Step 5: 运行完整验证。**

Run: `.venv\Scripts\python.exe -m pytest -q`

Run: `npm run build`（工作目录：`frontend`）

Run: `git diff --check`

Expected: 全部测试与构建成功；diff 检查无空白错误；不包含数据库、日志或密钥文件。

- [ ] **Step 6: 提交验收材料。**

```powershell
git add README.md docs/验收/A5物料统计模拟接口验收记录.md tests/backend/test_phase1_demo_readiness.py tests/backend/test_mock_integration_acceptance.py
git commit -m "docs: record mock integration acceptance"
```

## 计划自检

- 设计中的 A5 安全、幂等、数据范围、两个适配器、统计一致性、前端状态、测试和回滚均有对应任务。
- 所有新增生产行为先有失败测试，再写最小实现并运行聚焦回归。
- `IntegrationEvent` 是 A5 与物料外部事件共享的唯一幂等存储，不引入额外消息基础设施。
- 正式接口字段映射只位于 HTTP 适配器，业务服务不包含真实外部系统字段或密钥。
