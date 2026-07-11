import { http, unwrap } from './http'

export type AnalyticsAlertStatus = 'OPEN' | 'PROCESSING' | 'CLOSED'

export interface AnalyticsAlert {
  id: number
  alert_key: string
  title: string
  message: string
  severity: 'low' | 'medium' | 'high' | string
  source_module: string
  business_type?: string | null
  business_id?: number | null
  status: AnalyticsAlertStatus
  assignee_id?: number | null
  assignee_name?: string | null
  remark?: string | null
  opened_at?: string | null
  processed_at?: string | null
  closed_at?: string | null
}

export interface AnalyticsAlertCreate {
  alert_key: string
  title: string
  message: string
  severity: string
  source_module: string
  business_type?: string | null
  business_id?: number | null
}

export interface AnalyticsAlertUpdate {
  status?: AnalyticsAlertStatus
  remark?: string
}

export interface AnalyticsAlertList {
  total: number
  items: AnalyticsAlert[]
}

export function listAnalyticsAlerts(params: { status?: AnalyticsAlertStatus; page_size?: number } = {}) {
  return unwrap<AnalyticsAlertList>(http.get('/analytics-alerts', { params }))
}

export function createAnalyticsAlert(payload: AnalyticsAlertCreate) {
  return unwrap<AnalyticsAlert>(http.post('/analytics-alerts', payload))
}

export function updateAnalyticsAlert(alertId: number, payload: AnalyticsAlertUpdate) {
  return unwrap<AnalyticsAlert>(http.patch(`/analytics-alerts/${alertId}`, payload))
}
