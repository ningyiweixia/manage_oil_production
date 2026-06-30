import { http, unwrap } from './http'
import type { PageResult } from '../types/workover'

export type ContractorStatus = 'AVAILABLE' | 'BUSY' | 'OFFLINE'
export type OperationStatus = 'WAITING_DISPATCH' | 'DISPATCHED' | 'WORKING' | 'FINISHED' | 'CANCELED'

export interface ContractorCapacity {
  id: number
  contractor_name: string
  team_name: string
  report_date: string
  available_count: number
  status: ContractorStatus
  capability_tags: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface OperationSheet {
  id: number
  project_id: number
  contractor_capacity_id: number | null
  operation_no: string
  status: OperationStatus
  planned_start_at?: string | null
  planned_end_at?: string | null
  actual_start_at?: string | null
  actual_end_at?: string | null
  progress: number
  progress_detail: Record<string, unknown>
  a5_status?: string | null
  a5_remark?: string | null
  last_a5_sync_at?: string | null
  created_at: string
  updated_at: string
}

export interface ContractorQuery {
  page?: number
  page_size?: number
  contractor_name?: string
  report_date?: string
  status?: ContractorStatus | ''
}

export interface OperationSheetQuery {
  page?: number
  page_size?: number
  status?: OperationStatus | ''
  project_id?: number
  contractor_capacity_id?: number
}

function compact(params: object) {
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== '' && value !== undefined && value !== null))
}

export function listContractors(query: ContractorQuery) {
  return unwrap<PageResult<ContractorCapacity>>(http.get('/contractors/', { params: compact(query) }))
}

export function createContractor(payload: Omit<ContractorCapacity, 'id' | 'created_at' | 'updated_at'>) {
  return unwrap<ContractorCapacity>(http.post('/contractors/', payload))
}

export function updateContractor(id: number, payload: Partial<Omit<ContractorCapacity, 'id' | 'created_at' | 'updated_at'>>) {
  return unwrap<ContractorCapacity>(http.put(`/contractors/${id}`, payload))
}

export function listOperationSheets(query: OperationSheetQuery) {
  return unwrap<PageResult<OperationSheet>>(http.get('/contractors/operation-sheets/', { params: compact(query) }))
}

export function listPrioritySheets() {
  return unwrap<OperationSheet[]>(http.get('/contractors/priority-sheets'))
}

export function createOperationSheet(payload: { project_id: number; planned_start_at?: string; planned_end_at?: string }) {
  return unwrap<OperationSheet>(http.post('/contractors/operation-sheets/', payload))
}

export function dispatchOperation(payload: { operation_sheet_id: number; contractor_capacity_id: number }) {
  return unwrap<OperationSheet>(http.patch('/contractors/dispatch', payload))
}

export function updateOperationProgress(id: number, payload: { progress: number; progress_detail: Record<string, unknown> }) {
  return unwrap<OperationSheet>(http.patch(`/contractors/operation-sheets/${id}/progress`, payload))
}
