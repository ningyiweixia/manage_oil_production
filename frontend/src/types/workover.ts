export type ProjectPoolStatus =
  | 'DRAFT'
  | 'PENDING_GEOLOGY_VERIFY'
  | 'PENDING_PROCESS_VERIFY'
  | 'APPROVED'
  | 'REJECTED'
  | 'DISPATCHED'
  | 'VOIDED'

export interface WorkoverMeasure {
  measure_type: string
  process?: string
  construction_params: Record<string, unknown>
  duration_days?: number
  estimated_cost?: number
}

export interface WorkoverProject {
  id: number
  well_no: string
  well_name?: string
  layer?: string
  fault_description?: string
  territory_unit?: string
  block_name?: string
  report_unit: string
  production_priority: number
  status: ProjectPoolStatus
  reason?: string
  measures_jsonb: { measures?: WorkoverMeasure[] }
  remark?: string
  created_by_id?: number
  created_at: string
  updated_at: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiResponse<T> {
  code: number
  msg: string
  data: T
}

export interface ProjectQuery {
  page?: number
  page_size?: number
  block_name?: string
  well_no?: string
  status?: ProjectPoolStatus | ''
  measure_type?: string
}
