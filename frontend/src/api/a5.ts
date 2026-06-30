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

export function getA5SyncStatus() {
  return unwrap<A5SyncStatus>(http.get('/a5/sync/status'))
}

export function getA5Analytics(params: { start_date?: string; end_date?: string; category?: string } = {}) {
  return unwrap<A5Analytics>(http.get('/a5/analytics/summary', { params }))
}

export function triggerA5Sync() {
  return unwrap<{ task_id: string; message: string }>(http.post('/a5/sync/trigger'))
}

export function createA5SsoToken(wellNo: string, redirectPath = '/workorder') {
  return unwrap<A5Token>(http.post('/a5/sso-token', null, { params: { well_no: wellNo, redirect_path: redirectPath } }))
}
