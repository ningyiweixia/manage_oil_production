import { http, unwrap } from './http'

export interface A5SyncStatus {
  last_sync_time?: string | null
  last_sync_status: string
  last_sync_message: string
  sync_count_today: number
  is_running: boolean
}

export interface A5Token {
  token: string
  expire_at: string
  redirect_url: string
}

export interface A5MockMeasureReview {
  operation_no: string
  well_no: string
  status: string
  a5_status?: string | null
  a5_remark?: string | null
  contractor_name?: string | null
  team_name?: string | null
  measures: Array<Record<string, unknown>>
}

export interface A5NameValue {
  name: string
  value: number
}

export interface A5Analytics {
  anomaly_total: number
  special_process_total: number
  anomaly_distribution: A5NameValue[]
  process_distribution: A5NameValue[]
  trend: {
    days: string[]
    anomaly_counts: number[]
    process_counts: number[]
  }
}

export interface A5ReportFile {
  filename: string
  content_base64: string
  content_type: string
}

export interface A5SyncBatch {
  id: number
  sync_type: string
  status: string
  started_at: string
  finished_at?: string | null
  requested_operation_no?: string | null
  total_count: number
  updated_count: number
  unchanged_count: number
  not_found_count: number
  failed_count: number
  error_message?: string | null
}

export function getA5SyncStatus() {
  return unwrap<A5SyncStatus>(http.get('/a5/sync/status'))
}

export function listA5SyncLogs(limit = 20) {
  return unwrap<A5SyncBatch[]>(http.get('/a5/sync/logs', { params: { limit } }))
}

export function getA5Analytics(params: { start_date?: string; end_date?: string; category?: string } = {}) {
  return unwrap<A5Analytics>(http.get('/a5/analytics/summary', { params }))
}

export function exportA5AnalyticsReport(params: { start_date?: string; end_date?: string; category?: string; template_name?: string } = {}) {
  return unwrap<A5ReportFile>(http.get('/a5/analytics/report', { params }))
}

export function triggerA5Sync() {
  return unwrap<{ task_id: string; message: string }>(http.post('/a5/sync/trigger'))
}

export function createA5SsoToken(wellNo: string, redirectPath = '/workorder') {
  return unwrap<A5Token>(http.post('/a5/sso-token', null, { params: { well_no: wellNo, redirect_path: redirectPath } }))
}

export function getA5MockMeasureReview(token: string, operationNo: string) {
  return unwrap<A5MockMeasureReview>(http.get('/a5/mock/measure-review', { params: { token, operation_no: operationNo } }))
}

export function submitA5MockMeasureReview(payload: { token: string; operation_no: string; decision: 'DISPATCH' | 'REJECT'; remark?: string }) {
  return unwrap<{ operation_no: string; old_status: string; new_status: string; message: string }>(
    http.post('/a5/mock/measure-review/decision', payload)
  )
}
