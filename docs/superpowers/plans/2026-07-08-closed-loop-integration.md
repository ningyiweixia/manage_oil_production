# Closed Loop Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect project pool, operation sheets, A5, material, completion, and analytics through one visible operation closed-loop status.

**Architecture:** Keep the operation sheet as the central runtime aggregate. Material and A5 already write into operation sheet detail; completion records will now do the same, and the operation API will return a derived `closed_loop_status` object for frontend display.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, Vue 3, Element Plus, pytest, Vite.

---

### Task 1: Backend Closed Loop Contract

**Files:**
- Modify: `tests/backend/test_workover_operation_management_contract.py`
- Modify: `app/crud/completion.py`
- Modify: `app/services/workover_operation_service.py`

- [ ] Write tests that completion create/update/delete syncs `progress_detail.completion`.
- [ ] Write tests that operation enrichment returns `closed_loop_status`.
- [ ] Implement completion rollup sync using `operation_sheet_id`.
- [ ] Implement operation closed-loop summary from project, operation, A5, material, and completion.
- [ ] Run backend tests.

### Task 2: Frontend Closed Loop Display

**Files:**
- Modify: `frontend/src/api/workoverOperation.ts`
- Modify: `frontend/src/views/WorkoverOperationManageView.vue`
- Modify: `tests/backend/test_workover_operation_management_contract.py`

- [ ] Add frontend contract checks for `closed_loop_status`.
- [ ] Extend TypeScript API type.
- [ ] Display compact closed-loop tags in operation management table.
- [ ] Run frontend build.

### Task 3: Browser Verification

**Files:**
- No source files.

- [ ] Refresh `http://127.0.0.1:5173/workover/operation-sheets`.
- [ ] Confirm operation management page renders and closed-loop labels are visible.
