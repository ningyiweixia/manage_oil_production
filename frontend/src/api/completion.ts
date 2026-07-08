import { http, unwrap } from './http'
import type { PageResult } from '../types/workover'

export interface WellCompletionRecord {
  id: number
  well_no: string
  operation_sheet_id?: number | null
  measure_type: string
  completion_date?: string | null
  team_name?: string | null
  pre_repair_data: Record<string, unknown>
  post_repair_data: Record<string, unknown>
  remark?: string | null
  created_at: string
  updated_at: string
}

export interface WellCompletionQuery {
  page?: number
  page_size?: number
  well_no?: string
  measure_type?: string
  start_date?: string
  end_date?: string
}

export interface WellCompletionPayload {
  well_no: string
  operation_sheet_id?: number | null
  measure_type: string
  completion_date?: string
  team_name?: string
  pre_repair_data: Record<string, unknown>
  post_repair_data: Record<string, unknown>
  remark?: string
}

export interface CompletionAnalytics {
  total: number
  by_measure_type: Array<{ measure_type: string; count: number }>
}

export function listWellCompletions(query: WellCompletionQuery) {
  const params = Object.fromEntries(Object.entries(query).filter(([, value]) => value !== '' && value !== undefined && value !== null))
  return unwrap<PageResult<WellCompletionRecord>>(http.get('/well-completions/', { params }))
}

export function createWellCompletion(payload: WellCompletionPayload) {
  return unwrap<WellCompletionRecord>(http.post('/well-completions/', payload))
}

export function updateWellCompletion(id: number, payload: Partial<WellCompletionPayload>) {
  return unwrap<WellCompletionRecord>(http.put(`/well-completions/${id}`, payload))
}

export function deleteWellCompletion(id: number) {
  return unwrap<null>(http.delete(`/well-completions/${id}`))
}

export function getCompletionAnalytics() {
  return unwrap<CompletionAnalytics>(http.get('/well-completions/analytics/summary'))
}
