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

export function getA5SyncStatus() {
  return unwrap<A5SyncStatus>(http.get('/a5/sync/status'))
}

export function triggerA5Sync() {
  return unwrap<{ task_id: string; message: string }>(http.post('/a5/sync/trigger'))
}

export function createA5SsoToken(wellNo: string, redirectPath = '/workorder') {
  return unwrap<A5Token>(http.post('/a5/sso-token', null, { params: { well_no: wellNo, redirect_path: redirectPath } }))
}
