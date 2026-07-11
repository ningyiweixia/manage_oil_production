import { http, unwrap } from './http'
import type { PageResult, WorkoverMeasure } from '../types/workover'

export type ContractorStatus = 'AVAILABLE' | 'BUSY' | 'OFFLINE' | 'EXCEPTION'
export type ContractorSourceType = 'EXTERNAL_SYNC' | 'LOCAL_SUPPLEMENT' | 'SYNC_ERROR'
export type ContractorSyncStatus = 'SYNCED' | 'PENDING_CONFIRM' | 'CONFLICT' | 'INVALID'
export type ContractorSyncResultStatus = 'SUCCESS' | 'FAILED' | 'PARTIAL'
export type ContractorSyncType = 'SCHEDULED' | 'MANUAL' | 'SINGLE_TEAM'
export type OperationStatus = 'WAITING_DISPATCH' | 'DISPATCHED' | 'WORKING' | 'FINISHED' | 'CANCELED'

export interface ContractorCapacity {
  id: number
  contractor_name: string
  team_name: string
  report_date: string
  available_count: number
  status: ContractorStatus
  capability_tags: Record<string, unknown>
  external_system_id?: string | null
  external_status?: string | null
  source_type: ContractorSourceType
  sync_status: ContractorSyncStatus
  last_synced_at?: string | null
  sync_error_message?: string | null
  confirmed_at?: string | null
  confirmed_by_id?: number | null
  contact_name?: string | null
  contact_phone?: string | null
  qualification_expire_at?: string | null
  equipment_summary?: string | null
  occupied_count: number
  created_at: string
  updated_at: string
}

export interface ContractorCapacityPayload {
  contractor_name: string
  team_name: string
  report_date: string
  available_count: number
  status: ContractorStatus
  capability_tags: Record<string, unknown>
  external_system_id?: string | null
  external_status?: string | null
  source_type?: ContractorSourceType
  sync_status?: ContractorSyncStatus
  sync_error_message?: string | null
  contact_name?: string | null
  contact_phone?: string | null
  qualification_expire_at?: string | null
  equipment_summary?: string | null
}

export interface ContractorSyncLog {
  id: number
  sync_type: ContractorSyncType
  status: ContractorSyncResultStatus
  started_at: string
  finished_at?: string | null
  success_count: number
  failed_count: number
  created_count: number
  updated_count: number
  ignored_count: number
  error_message?: string | null
  operator_id?: number | null
  raw_summary: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface ContractorSyncSummary {
  connection_status: string
  last_sync_time?: string | null
  last_sync_status?: ContractorSyncResultStatus | null
  created_count: number
  updated_count: number
  ignored_count: number
  failed_count: number
  exception_count: number
}

export interface ContractorOverview {
  reported_team_count: number
  available_team_count: number
  busy_team_count: number
  offline_team_count: number
  sync_exception_count: number
  major_repair_team_count: number
}

export interface ContractorOperationLink {
  id: number
  operation_no: string
  status: OperationStatus
  well_no?: string | null
  dispatch_time?: string | null
  a5_status?: string | null
  created_at: string
}

export interface OperationSheet {
  id: number
  project_id: number
  project_well_no?: string | null
  project?: {
    id: number
    well_no?: string | null
    block_name?: string | null
    territory_unit?: string | null
    report_unit?: string | null
    data_source?: string | null
    measures_jsonb?: { measures?: WorkoverMeasure[] }
    approved_at?: string | null
  } | null
  contractor_capacity_id: number | null
  contractor?: {
    id: number
    contractor_name: string
    team_name: string
    report_date?: string | null
    status?: ContractorStatus | string
  } | null
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

export interface DispatchA5Result {
  sheet: OperationSheet
  redirect_url: string
  token: string
  expire_at: string
}

export interface ContractorQuery {
  page?: number
  page_size?: number
  contractor_name?: string
  team_name?: string
  report_date?: string
  status?: ContractorStatus | ''
  capability_tag?: string
  source_type?: ContractorSourceType | ''
  sync_status?: ContractorSyncStatus | ''
}

export interface OperationSheetQuery {
  page?: number
  page_size?: number
  status?: OperationStatus | ''
  project_id?: number
  contractor_capacity_id?: number
  well_no?: string
  block_name?: string
  contractor_keyword?: string
  start_date?: string
  end_date?: string
}

function compact(params: object) {
  return Object.fromEntries(Object.entries(params).filter(([, value]) => value !== '' && value !== undefined && value !== null))
}

export function listContractors(query: ContractorQuery) {
  return unwrap<PageResult<ContractorCapacity>>(http.get('/contractors/', { params: compact(query) }))
}

export function getContractorSyncSummary() {
  return unwrap<ContractorSyncSummary>(http.get('/contractors/sync-summary'))
}

export function getContractorOverview(reportDate?: string) {
  return unwrap<ContractorOverview>(http.get('/contractors/overview', { params: compact({ report_date: reportDate }) }))
}

export function syncContractors(payload: { report_date?: string }) {
  return unwrap<ContractorSyncLog>(http.post('/contractors/sync', payload))
}

export function syncSingleContractor(id: number) {
  return unwrap<ContractorSyncLog>(http.post(`/contractors/${id}/sync`))
}

export function confirmContractor(id: number) {
  return unwrap<ContractorCapacity>(http.patch(`/contractors/${id}/confirm`))
}

export function markContractorException(id: number, reason: string) {
  return unwrap<ContractorCapacity>(http.patch(`/contractors/${id}/exception`, { reason }))
}

export function resolveContractorException(id: number) {
  return unwrap<ContractorCapacity>(http.patch(`/contractors/${id}/resolve-exception`))
}

export function listContractorSyncLogs(query: { page?: number; page_size?: number; status?: ContractorSyncResultStatus | ''; sync_type?: ContractorSyncType | '' }) {
  return unwrap<PageResult<ContractorSyncLog>>(http.get('/contractors/sync-logs', { params: compact(query) }))
}

export function listContractorOperationSheets(id: number) {
  return unwrap<ContractorOperationLink[]>(http.get(`/contractors/${id}/operation-sheets`))
}

export function createContractor(payload: ContractorCapacityPayload) {
  return unwrap<ContractorCapacity>(http.post('/contractors/', payload))
}

export function updateContractor(id: number, payload: Partial<ContractorCapacityPayload>) {
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

export function dispatchOperation(payload: { operation_sheet_id: number; contractor_capacity_id: number; redirect_path?: string }) {
  return unwrap<DispatchA5Result>(http.patch('/contractors/dispatch', payload))
}

export function updateOperationProgress(id: number, payload: { progress: number; progress_detail: Record<string, unknown> }) {
  return unwrap<OperationSheet>(http.patch(`/contractors/operation-sheets/${id}/progress`, payload))
}

export interface OperationAnalytics {
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
  team_workload: { team_name: string; sheet_count: number }[]
  measure_type_distribution: { measure_type: string; count: number }[]
  anomaly_count: number
}

export function getOperationAnalytics() {
  return unwrap<OperationAnalytics>(http.get('/contractors/analytics/summary'))
}
