# Data Analytics Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a usable analytics module whose filters, KPIs, exports, traceability, data-quality checks, and alert workflow are logically consistent.

**Architecture:** Keep the existing FastAPI/Vue aggregation boundary. Introduce focused query-aware adapters and quality/alert services, expose stable API contracts, and make the dashboard reuse one query object for screen, export, and drill-down.

**Tech Stack:** FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, SQLite/PostgreSQL, openpyxl, python-docx, Vue 3, TypeScript, Element Plus, ECharts.

---

### Task 1: Make every analytics filter effective

**Files:**
- Modify: `app/services/statistics_analysis_service.py`
- Modify: `app/services/workover_operation_service.py`
- Modify: `app/crud/material.py`
- Modify: `app/crud/completion.py`
- Test: `tests/backend/test_statistics_analysis_filters.py`

- [ ] Write tests proving `report_unit`, `team_name`, `material_status`, dates, well, block, measure and status reach the applicable query layer.
- [ ] Run `python -m unittest tests.backend.test_statistics_analysis_filters -v` and verify failures identify ignored filters.
- [ ] Add explicit query dataclasses/parameters to each adapter and apply SQLAlchemy predicates before aggregation.
- [ ] Return stable zero values for empty result sets and reject `start_date > end_date`.
- [ ] Re-run focused tests and the existing statistics contract tests.

### Task 2: Stabilize KPI and export contracts

**Files:**
- Modify: `app/services/statistics_analysis_service.py`
- Modify: `app/services/report_service.py`
- Modify: `app/api/v1/endpoints/reports.py`
- Modify: `frontend/src/api/reports.ts`
- Test: `tests/backend/test_statistics_exports.py`

- [ ] Write failing tests for average approval/dispatch duration, on-time completion, material arrival rate, contractor utilization, and query-aware Excel/Word exports.
- [ ] Verify exports fail before implementation because dedicated endpoints or query propagation are absent.
- [ ] Implement KPI helpers with documented denominators and two-decimal rounding.
- [ ] Add `/statistics-analysis.xlsx` and `/statistics-analysis.docx` endpoints using the same `StatisticsAnalysisQuery` as the screen endpoint.
- [ ] Update frontend API types and download functions without compatibility normalization hiding missing fields.
- [ ] Run focused backend tests and `npm run build`.

### Task 3: Add data-quality checks

**Files:**
- Create: `app/services/data_quality_service.py`
- Create: `app/schemas/analytics.py`
- Modify: `app/api/v1/endpoints/reports.py`
- Test: `tests/backend/test_data_quality_service.py`

- [ ] Write failing tests for missing task/A5 links, invalid time ordering, excessive material usage, missing completion data, expiring qualification, and sync failure.
- [ ] Implement independent rule functions returning a common issue schema.
- [ ] Add a read-only `/reports/data-quality` endpoint protected by `report:read`.
- [ ] Include the quality summary in `build_statistics_analysis` without changing source business records.
- [ ] Run focused tests and all existing backend tests.

### Task 4: Add persistent alert workflow

**Files:**
- Create: `app/models/analytics.py`
- Modify: `app/models/__init__.py`
- Create: `app/schemas/analytics_alert.py`
- Create: `app/crud/analytics_alert.py`
- Create: `app/services/analytics_alert_service.py`
- Create: `app/api/v1/endpoints/analytics.py`
- Modify: `app/api/v1/router.py`
- Create: `alembic/versions/20260711_0015_analytics_alerts.py`
- Test: `tests/backend/test_analytics_alert_workflow.py`

- [ ] Write failing model/service tests for active-alert idempotency and allowed `OPEN -> PROCESSING -> CLOSED` transitions.
- [ ] Add reversible migration and SQLite-compatible SQLAlchemy models.
- [ ] Implement list and patch APIs with audit-friendly assignee, remark and timestamps.
- [ ] Register `analytics:alert:read` and `analytics:alert:handle` permissions in seed data.
- [ ] Run migration/model/service/API contract tests.

### Task 5: Make the dashboard operational

**Files:**
- Modify: `frontend/src/views/AnalyticsDashboard.vue`
- Modify: `frontend/src/api/reports.ts`
- Create: `frontend/src/api/analyticsAlerts.ts`
- Modify: `frontend/src/router/index.ts`
- Test: `tests/backend/test_frontend_analytics_contract.py`

- [ ] Write failing contract tests for query reuse, dedicated export URLs, quality summary, alert handling and drill-down route construction.
- [ ] Add KPI cards for approval/dispatch time, on-time completion, material arrival and contractor utilization.
- [ ] Add data-quality and alert panels with loading, empty and error states.
- [ ] Make chart clicks route to the relevant ledger with filters encoded in query parameters.
- [ ] Ensure screen refresh, URL restoration and exports all use one normalized query object.
- [ ] Run frontend contract tests and `npm run build`.

### Task 6: Integrated verification and handoff

**Files:**
- Modify: `docs/功能验收清单.md`
- Create: `docs/数据分析模块实施与验收.md`

- [ ] Run all backend tests with local placeholder secrets and SQLite.
- [ ] Run the frontend production build.
- [ ] Start isolated backend and frontend on non-conflicting ports and smoke-test analytics, exports, quality and alert endpoints.
- [ ] Compare dashboard and exported values for a fixed seeded query.
- [ ] Review the diff for unrelated generated files, secrets and user-owned changes.
- [ ] Record commands, results, known operational limits and rollback steps in the acceptance document.
