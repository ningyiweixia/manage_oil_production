import { http, unwrap } from './http'
import type { PageResult } from '../types/workover'
import type { OperationSheet, OperationSheetQuery, OperationStatus } from './contractor'

export interface OperationDashboard {
  total_sheets: number
  status_distribution: {
    waiting_dispatch: number
    dispatched: number
    working: number
    finished: number
    canceled: number
  }
  dispatch_rate: number
  completion_rate: number
  anomaly_count: number
  runtime_focus: {
    waiting: number
    dispatched?: number
    working: number
    finished: number
    material_total: number
    completion_total: number
    a5_synced: number
  }
  status_tabs: OperationStatus[]
}

export interface ManagedOperationSheet extends OperationSheet {
  material_status?: {
    status: string
    total: number
    counts?: Record<string, number>
  }
  completion_status?: {
    status: string
    total: number
  }
  closed_loop_status?: {
    overall: 'PENDING' | 'IN_PROGRESS' | 'COMPLETE' | string
    done_count: number
    total_count: number
    stages: Array<{
      key: string
      label: string
      status: string
      done: boolean
    }>
  }
}

function compact(params: object) {
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== '' && value !== undefined && value !== null))
}

export function listWorkoverOperationSheets(query: OperationSheetQuery) {
  return unwrap<PageResult<ManagedOperationSheet>>(http.get('/workover-operations/sheets/', { params: compact(query) }))
}

export function listPriorityWorkoverOperationSheets() {
  return unwrap<ManagedOperationSheet[]>(http.get('/workover-operations/priority-sheets'))
}

export function getWorkoverOperationDashboard() {
  return unwrap<OperationDashboard>(http.get('/workover-operations/dashboard'))
}

export function createWorkoverOperationSheet(payload: { project_id: number; planned_start_at?: string; planned_end_at?: string }) {
  return unwrap<ManagedOperationSheet>(http.post('/workover-operations/sheets/', payload))
}

export function updateWorkoverOperationProgress(id: number, payload: { progress: number; progress_detail: Record<string, unknown> }) {
  return unwrap<ManagedOperationSheet>(http.patch(`/workover-operations/sheets/${id}/progress`, payload))
}
