# A5 Material Analytics Closed-Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a production-oriented closed loop in which A5 events are durably received and retried, material requirements progress through an auditable lifecycle, and statistics support overview, metric drill-down, and well traceability from one consistent query model.

**Architecture:** Keep the existing FastAPI/Vue boundary and existing public URLs. Add a configurable Local/HTTP A5 adapter behind a durable integration-event inbox, move material transitions into a domain service with immutable flow logs, and expose analytics through one query service reused by screen, drill-down, well trace, and exports. PostgreSQL remains the source of truth; Redis is cache only; Celery worker/beat process retries and scheduled synchronization.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL/SQLite, Redis, Celery, pytest, Vue 3, TypeScript, Element Plus, ECharts, Docker Compose.

---

### Task 1: Lock down A5 configuration and adapter boundaries

**Files:**
- Modify: `app/core/config.py`
- Create: `app/services/a5_adapter.py`
- Modify: `.env.example`
- Modify: `deploy/deploy.sh`
- Test: `tests/backend/test_a5_adapter_config.py`

- [ ] Add a failing configuration test proving `A5_ADAPTER_MODE=local` selects the deterministic local adapter, `http` selects the real client adapter, an unsupported value is rejected, and production startup rejects missing/placeholder signing credentials.

  ```python
  def test_a5_adapter_mode_rejects_unknown_value(monkeypatch):
      monkeypatch.setenv("A5_ADAPTER_MODE", "invalid")
      with pytest.raises(ValidationError):
          Settings()


  def test_production_rejects_placeholder_a5_secret(monkeypatch):
      monkeypatch.setenv("ENVIRONMENT", "prod")
      monkeypatch.setenv("A5_API_SECRET", "change-me")
      with pytest.raises(ValidationError, match="A5_API_SECRET"):
          Settings()
  ```

- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_adapter_config.py -q` and verify it fails because the adapter mode and production credential guard do not exist.
- [ ] Add typed settings for adapter mode, base URL, timeout, app key, API secret, callback secret, and retry limits. Treat blank and known sample values as invalid in `prod` without printing secret values.
- [ ] Define an `A5Adapter` protocol and `LocalA5Adapter`/`HttpA5Adapter` implementations. Make the local adapter return stable data derived from the input operation number, never random data.

  ```python
  class A5Adapter(Protocol):
      def submit_operation(self, payload: dict[str, Any]) -> A5AdapterResult: ...
      def query_operation(self, a5_task_id: str) -> A5AdapterResult: ...


  def build_a5_adapter(settings: Settings) -> A5Adapter:
      if settings.a5_adapter_mode == "local":
          return LocalA5Adapter()
      return HttpA5Adapter(A5Client.from_settings(settings))
  ```

- [ ] Remove deploy-time copying of usable default passwords/secrets. Keep only explicit placeholders in `.env.example`, and make deployment abort with a readable list of missing variables before containers start.
- [ ] Re-run the focused test, then run `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_sync_service.py -q` to prove the legacy A5 client contract still passes.
- [ ] Commit only these files with `git commit -m "feat: add secure A5 adapter configuration"`.

### Task 2: Add the durable integration-event inbox

**Files:**
- Create: `app/models/integration.py`
- Modify: `app/models/__init__.py`
- Create: `app/schemas/integration.py`
- Create: `app/services/integration_event_service.py`
- Modify: `app/db/local_schema.py`
- Create: `alembic/versions/20260713_0016_a5_material_closed_loop.py`
- Test: `tests/backend/test_integration_event_service.py`

- [ ] Write failing tests for event idempotency, payload-hash conflict detection, retry scheduling, terminal failure, and pending-review state. Use a temporary SQLite database so the tests exercise real uniqueness constraints.

  ```python
  first = service.receive(
      source="A5",
      event_key="task-001:approved",
      event_type="OPERATION_APPROVED",
      operation_no="OP-001",
      payload={"status": "approved"},
  )
  duplicate = service.receive(
      source="A5",
      event_key="task-001:approved",
      event_type="OPERATION_APPROVED",
      operation_no="OP-001",
      payload={"status": "approved"},
  )
  assert duplicate.id == first.id
  assert duplicate.delivery_count == 2

  with pytest.raises(EventConflictError):
      service.receive(
          source="A5",
          event_key="task-001:approved",
          event_type="OPERATION_APPROVED",
          operation_no="OP-001",
          payload={"status": "rejected"},
      )
  ```

- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_integration_event_service.py -q` and verify failure because the table and service are absent.
- [ ] Add `IntegrationSyncEvent` with source/event key unique constraint, payload and hash, processing status, retry counters, next retry, last error, operation number, trace ID, review note, and timestamps. Keep raw payload for audit, but cap stored error text and never store secrets.
- [ ] Implement transitions `PENDING -> PROCESSING -> PROCESSED`, `PROCESSING -> PENDING` for a scheduled retry, and `PENDING/PROCESSING -> PENDING_REVIEW|FAILED`. Use an atomic insert-or-read pattern and compare payload hashes on duplicates.
- [ ] Add a reversible Alembic migration with indexes on `(status, next_retry_at)`, `(operation_no, created_at)`, and `(source, event_type, created_at)`. Register the table in SQLite local schema initialization.
- [ ] Re-run the focused test and run `.venv\Scripts\python.exe -m pytest tests/backend/test_database_unavailable.py -q`.
- [ ] Commit with `git commit -m "feat: persist idempotent integration events"`.

### Task 3: Make A5 callbacks secure, idempotent, and retryable

**Files:**
- Modify: `app/services/a5_auth_service.py`
- Modify: `app/services/a5_sync_service.py`
- Modify: `app/api/v1/endpoints/a5_integration.py`
- Modify: `app/tasks/a5_tasks.py`
- Modify: `celery_app.py`
- Test: `tests/backend/test_a5_event_workflow.py`
- Test: `tests/backend/test_a5_sync_service.py`

- [ ] Write a failing endpoint/service test proving lower-cased ASGI header names still validate, a correct HMAC callback succeeds exactly once, callbacks both with and without an external event ID derive stable idempotency keys, a repeated callback is idempotent, a same-key/different-payload callback is rejected, an unknown operation enters pending review, and a transient adapter error schedules a retry.

  ```python
  headers = {
      "x-a5-signature": sign(body, secret),
      "x-a5-timestamp": str(timestamp),
      "x-a5-event-id": "evt-001",
  }
  response = client.post("/api/v1/a5/callback", content=body, headers=headers)
  assert response.status_code == 200
  assert event_repo.count(event_key="evt-001") == 1
  ```

- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_a5_event_workflow.py -q` and confirm the current case-sensitive lookup and non-persistent callback path fail.
- [ ] Normalize header keys once in the authentication service, enforce timestamp skew and constant-time HMAC comparison, and use separate callback secret with an explicit compatibility fallback only outside production.
- [ ] Change callback processing to first persist the event, then apply it to the matching operation sheet in one controlled service transaction. Route unverifiable business references to `PENDING_REVIEW` instead of silently dropping them.
- [ ] Add Celery tasks `process_integration_event(event_id)` and `retry_due_integration_events()` with bounded exponential backoff and terminal failure after the configured attempt limit. Use database locks or compare-and-set status so two workers cannot process one event concurrently.
- [ ] Return A5 integration status from the durable event table, including pending/processed/retrying/review/failed counts, retry count, latest success time, and most recent error timestamp; Redis may cache the result but cannot be the only source. Reuse the existing alert webhook when consecutive failures reach the configured threshold.
- [ ] Run both A5 focused test files and `.venv\Scripts\python.exe -m pytest tests/backend/test_phase1_demo_readiness.py -q`.
- [ ] Commit with `git commit -m "feat: close the A5 callback and retry loop"`.

### Task 4: Introduce the material lifecycle and immutable flow log

**Files:**
- Modify: `app/models/material.py`
- Modify: `app/models/__init__.py`
- Modify: `app/schemas/material.py`
- Create: `app/services/material_workflow_service.py`
- Modify: `app/db/local_schema.py`
- Modify: `alembic/versions/20260713_0016_a5_material_closed_loop.py`
- Test: `tests/backend/test_material_workflow_service.py`

- [ ] Write failing domain tests for the allowed lifecycle, forbidden skips/backtracking, cancellation boundary, optimistic version conflict, quantitative invariants, exception recording, supplementary requests, and one immutable log row per successful transition.

  ```python
  ALLOWED = [
      "PENDING", "APPROVED", "PLANNED", "DELIVERED",
      "IN_TRANSIT", "ARRIVED", "USED", "CLOSED",
  ]
  for target in ALLOWED[1:]:
      requirement = workflow.transition(requirement.id, target, actor_id=1)

  with pytest.raises(InvalidMaterialTransition):
      workflow.transition(requirement.id, "PLANNED", actor_id=1)
  ```

- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_material_workflow_service.py -q` and verify the existing CRUD permits invalid direct status updates and lacks the new states/log.
- [ ] Extend `MaterialRequirementStatus` with `IN_TRANSIT` and `CLOSED`, retaining `DELIVERED` as the existing “已出库” meaning. Add returned/loss/supplement quantities, parent requirement, version, structured exception code/detail, close/cancel fields, and applicable timestamps.
- [ ] Add `MaterialFlowLog` with requirement ID, from/to status, actor, quantity snapshot, event source/key, remark, trace ID, and timestamp. Do not expose update/delete operations for this model.
- [ ] Implement the transition map and invariants in one domain service:

  ```python
  assert 0 <= used_quantity <= arrived_quantity
  assert 0 <= returned_quantity <= arrived_quantity - used_quantity
  assert 0 <= loss_quantity <= arrived_quantity - used_quantity - returned_quantity
  assert delivered_quantity <= planned_quantity + supplement_quantity
  ```

- [ ] Permit idempotent replay when `event_source + event_key` already produced the same transition; reject contradictory replay. Use a version column for user edits and row locking for server-side transitions.
- [ ] Extend the shared migration with columns, foreign keys, check constraints, unique event-log key, and query indexes. Ensure existing records map safely without changing the meaning of `DELIVERED`.
- [ ] Re-run focused tests and `.venv\Scripts\python.exe -m pytest tests/backend/test_material_closed_loop_contract.py -q`.
- [ ] Commit with `git commit -m "feat: add auditable material lifecycle"`.

### Task 5: Route material APIs through the workflow and roll up readiness

**Files:**
- Modify: `app/crud/material.py`
- Modify: `app/api/v1/endpoints/materials.py`
- Modify: `app/services/workover_operation_service.py`
- Modify: `app/schemas/material.py`
- Test: `tests/backend/test_material_closed_loop_api.py`
- Test: `tests/backend/test_material_closed_loop_contract.py`

- [ ] Write failing API/service tests for scoped list access, transition command, flow history, exception handling, supplementary request creation, operation rollup, and concurrent version conflict. Include a user from another reporting unit to prove the data-scope boundary.

  ```python
  response = client.post(
      f"/api/v1/materials/{requirement_id}/transition",
      json={"target_status": "PLANNED", "version": 1, "remark": "排料完成"},
      headers=auth_headers,
  )
  assert response.json()["data"]["status"] == "PLANNED"
  ```

- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_material_closed_loop_api.py -q` and verify the command/history endpoints do not exist.
- [ ] Prevent generic update APIs from directly changing lifecycle status or server-owned quantities. Add the approved explicit endpoints: `POST /materials/{id}/transition`, `POST /materials/{id}/supplements`, `POST /materials/{id}/exceptions`, `PATCH /materials/{id}/exceptions/resolve`, and `GET /materials/{id}/timeline`, using existing response envelopes and permission dependencies.
- [ ] Apply reporting-unit/role data scope to all material reads, writes, history, and analytics. Return HTTP 409 for stale version or invalid transition and keep business error codes in the response body.
- [ ] Compute operation-level material state from all active requirements:

  | Rollup | Rule |
  |---|---|
  | `NOT_READY` | No active requirement has reached `ARRIVED` |
  | `PARTIAL_READY` | Some but not all required quantities have arrived |
  | `READY_AT_SITE` | All active required quantities have arrived and no unresolved exception exists |
  | `EXCEPTION` | Any unresolved material exception exists |
  | `CLOSED` | Every active requirement is `CLOSED` or `CANCELED` |

- [ ] Store the compatibility rollup in `WorkoverOperationSheet.progress_detail.material_status`, recalculate it in the same transaction after every material mutation, and return it through existing operation APIs.
- [ ] Run both focused material suites and `.venv\Scripts\python.exe -m pytest tests/backend/test_workover_operation_management_contract.py -q`.
- [ ] Commit with `git commit -m "feat: expose material workflow and readiness"`.

### Task 6: Build one statistics query model and database fact adapters

**Files:**
- Modify: `app/services/statistics_analysis_service.py`
- Modify: `app/services/report_service.py`
- Modify: `app/api/v1/endpoints/reports.py`
- Modify: `app/schemas/analytics.py`
- Test: `tests/backend/test_statistics_closed_loop_metrics.py`
- Test: `tests/backend/test_statistics_analysis_filters.py`
- Test: `tests/backend/test_statistics_exports.py`

- [ ] Write failing tests with fixed database fixtures for A5 success rate, A5 pending-review count, material readiness rate, material exception count, material cycle duration, completion rate, and average operation duration. Document each numerator, denominator, time boundary, and empty-data result in test names/fixtures.

  ```python
  result = service.build(query)
  assert result["kpis"]["a5_success_rate"] == 75.0
  assert result["kpis"]["material_ready_rate"] == 50.0
  assert result["kpis"]["material_exception_count"] == 1
  ```

- [ ] Add cross-output tests proving overview, drill-down, well trace, Excel, and Word use the same filters, data scope, and total counts. Verify Redis failure does not change correctness.
- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_statistics_closed_loop_metrics.py tests/backend/test_statistics_analysis_filters.py tests/backend/test_statistics_exports.py -q` and confirm missing metrics/fact adapters fail.
- [ ] Define one typed `StatisticsAnalysisQuery` with date, reporting unit, team, block, well, measure, operation status, material status, A5 status, and contractor filters. Reject reversed dates and normalize only at the API boundary.
- [ ] Add database-backed fact adapters for operation sheets, integration events, material requirements/logs, completions, approvals, and contractors. Keep each metric definition in a named helper and round only the final displayed value.
- [ ] Make `build_statistics_analysis`, Excel, and Word consume the same service result. Cache only serialized results using a key derived from normalized query + user scope; fall back to direct DB queries on cache miss/error.
- [ ] Re-run the three focused test files and `.venv\Scripts\python.exe -m pytest tests/backend/test_statistics_analysis_contract.py -q`.
- [ ] Commit with `git commit -m "feat: unify closed-loop statistics metrics"`.

### Task 7: Add metric drill-down and well trace APIs

**Files:**
- Modify: `app/services/statistics_analysis_service.py`
- Modify: `app/api/v1/endpoints/reports.py`
- Modify: `app/schemas/analytics.py`
- Test: `tests/backend/test_statistics_drilldown.py`

- [ ] Write failing API/service tests for supported metric codes, unsupported metric rejection, pagination, scope enforcement, filter propagation, and chronological well trace assembly.

  ```python
  response = client.get(
      "/api/v1/reports/statistics-analysis/drilldown",
      params={"metric_code": "material_exception_count", "page": 1, "page_size": 20},
  )
  assert response.json()["data"]["total"] == overview_exception_count

  trace = client.get("/api/v1/reports/statistics-analysis/wells/WELL-001")
  occurred_at_values = [
      item["occurred_at"]
      for item in trace.json()["data"]["timeline"]
  ]
  assert occurred_at_values == sorted(occurred_at_values)
  ```

- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_statistics_drilldown.py -q` and verify both endpoints are absent.
- [ ] Add `GET /reports/statistics-analysis/drilldown` with an allowlist mapping of metric codes to fact queries. Return metric definition, current filters, pagination, and rows with stable navigation identifiers.
- [ ] Add `GET /reports/statistics-analysis/wells/{well_no}` with optional `operation_sheet_id`, returning well summary plus a normalized six-stage timeline from project pool, approval/dispatch, operation, A5 event, material flow/exception, and completion/operation-log records. Include source type/source ID instead of leaking raw payloads.
- [ ] Apply the current user's data scope before totals, pagination, and timeline assembly; inaccessible wells must return 404 to avoid revealing existence.
- [ ] Re-run the focused test and all statistics tests with `.venv\Scripts\python.exe -m pytest tests/backend/test_statistics_*.py -q`.
- [ ] Commit with `git commit -m "feat: add analytics drilldown and well trace"`.

### Task 8: Turn the three frontend modules into one operational loop

**Files:**
- Modify: `frontend/src/api/a5.ts`
- Modify: `frontend/src/api/material.ts`
- Modify: `frontend/src/api/reports.ts`
- Modify: `frontend/src/views/A5IntegrationView.vue`
- Modify: `frontend/src/views/MaterialManageView.vue`
- Modify: `frontend/src/views/AnalyticsDashboard.vue`
- Modify: `frontend/src/router/index.ts`
- Test: `tests/backend/test_frontend_closed_loop_contract.py`
- Test: `tests/backend/test_frontend_analytics_contract.py`
- Test: `tests/backend/test_frontend_material_closed_loop_contract.py`

- [ ] Write failing frontend contract tests for typed event status, retry/review actions, transition/history APIs, operation readiness, shared analytics query, clickable metrics, drill-down paging, well trace navigation, loading/empty/error states, and URL-restorable filters.
- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_frontend_closed_loop_contract.py tests/backend/test_frontend_analytics_contract.py tests/backend/test_frontend_material_closed_loop_contract.py -q` and verify the new APIs/interactions are missing.
- [ ] In `A5IntegrationView.vue`, replace cache-only status presentation with durable event counters and a paginated exception/review list. Expose retry and review actions only when the user's permissions allow them; require a review note for manual resolution.
- [ ] In `MaterialManageView.vue`, show the lifecycle stepper, quantitative balance, unresolved exception badge, operation readiness, supplementary relationship, version-conflict refresh, and read-only flow timeline. Submit lifecycle changes only through the transition API.
- [ ] In `AnalyticsDashboard.vue`, keep one reactive query object synchronized with route query parameters. Make KPI cards/charts navigate to a drill-down panel/route, then allow a row to open the well trace timeline without losing the original filter context.
- [ ] Add TypeScript discriminated unions for statuses and API response shapes. Do not add fallback aliases that hide missing backend fields; surface schema mismatch as an error state.
- [ ] Run the three contract suites and `npm run build` from `frontend`. Fix all TypeScript and production-bundle errors.
- [ ] Commit with `git commit -m "feat: connect A5 material and analytics UI"`.

### Task 9: Run asynchronous workers and scheduled retries in deployment

**Files:**
- Modify: `docker-compose.yml`
- Modify: `celery_app.py`
- Modify: `README.md`
- Test: `tests/backend/test_deployment_workers_contract.py`

- [ ] Write a failing deployment contract test that parses Compose YAML and asserts `celery-worker` and `celery-beat` use the backend image/config, wait for PostgreSQL/Redis health, load no sample secrets, and have restart/health behavior appropriate to their process type.

  ```python
  services = compose["services"]
  assert services["celery-worker"]["command"] == [
      "celery", "-A", "celery_app.celery_app", "worker", "--loglevel=INFO"
  ]
  assert "celery-beat" in services
  ```

- [ ] Run `.venv\Scripts\python.exe -m pytest tests/backend/test_deployment_workers_contract.py -q` and verify the services are absent.
- [ ] Add worker and beat services reusing the backend build, environment, volumes, networks, health dependencies, and non-root runtime. Give beat a persistent schedule volume or database-safe scheduler strategy and prevent duplicate beat instances.
- [ ] Register integration retry, A5 polling, and periodic reconciliation schedules with explicit task names and time limits. Keep business writes idempotent so task redelivery is safe.
- [ ] Document local adapter mode, real A5 activation checklist, callback secret rotation, retry/review operations, material lifecycle, worker startup, and rollback procedure in `README.md` without overwriting the user's unrelated README edits.
- [ ] Run the focused test and `docker compose config --quiet`.
- [ ] Commit with `git commit -m "ops: run A5 retry workers in compose"`.

### Task 10: Integrated verification and acceptance evidence

**Files:**
- Create: `docs/验收/A5物料统计统一闭环验收记录.md`
- Modify only if a test exposes a defect: files listed in Tasks 1–9

- [ ] Run the complete backend suite with `.venv\Scripts\python.exe -m pytest -q` and record the test count and duration. No test may rely on the developer's persistent `local_dev.db`.
- [ ] Run `npm run build` in `frontend` and record the exact result. Run `docker compose config --quiet` and verify no resolved environment output is copied into the acceptance document.
- [ ] Apply Alembic upgrade to a disposable SQLite/PostgreSQL test database, then downgrade one revision and upgrade again. Confirm both the integration event and material log schemas survive the cycle.
- [ ] Start backend/frontend using `.local/start-backend.ps1` and `.local/start-frontend.ps1` on non-conflicting ports. Smoke-test login, A5 local submit/callback/retry, the complete material transition sequence, analytics overview/drill-down/well trace, and Excel/Word export.
- [ ] Verify values against a fixed scenario: one successful A5 event, one retrying event, two material requirements (one ready, one exception), and one completion. Confirm overview totals equal drill-down totals and exported totals.
- [ ] Test failure paths: invalid signature, duplicate event, conflicting duplicate, unknown operation, Redis unavailable, stale material version, forbidden transition, unauthorized reporting unit, and worker task redelivery.
- [ ] Review `git status --short`, `git diff --check`, and `git diff --stat` so generated databases/logs, credentials, user-owned changes, and unrelated files are not included.
- [ ] Write the acceptance record with commands, observed results, screenshots/response excerpts where useful, known limitation that real A5/material endpoints are not yet available, activation checklist for HTTP mode, and rollback instructions.
- [ ] Run the verification-before-completion checklist before claiming success. Commit the acceptance record with `git commit -m "docs: record closed-loop acceptance evidence"`.

## Definition of Done

- [ ] A5 callbacks are case-insensitively authenticated, durably persisted, idempotent, retryable, reviewable, and observable without depending on Redis for truth.
- [ ] Local A5 mode enables full verification without real external interfaces; production HTTP mode fails closed when credentials are missing or placeholders.
- [ ] Material requirements can only move through the approved lifecycle, every transition is traceable, quantity invariants hold, and operation readiness is recalculated transactionally.
- [ ] Statistics overview, drill-down, well trace, Excel, and Word share one normalized query and the same scoped database facts.
- [ ] A5, material, and analytics views expose one navigable business loop with explicit loading, empty, error, conflict, and permission states.
- [ ] Celery worker/beat are deployable, retries are bounded, task delivery is idempotent, migrations are reversible, all tests pass, and user-owned worktree changes remain untouched.
