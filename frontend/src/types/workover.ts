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
  rejected_from_status?: ProjectPoolStatus | null
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

export interface AnalyticsQuery {
  start_date?: string
  end_date?: string
  block_name?: string
  status?: ProjectPoolStatus | ''
  measure_type?: string
}

export interface AnalyticsKpis {
  total_projects: number
  pending_approvals: number
  approval_rate: number
  estimated_cost: number
  average_priority: number
}

export interface StatusCount {
  status: ProjectPoolStatus
  label: string
  count: number
}

export interface NameValue {
  name: string
  value: number
}

export interface HeatmapSummary {
  blocks: string[]
  statuses: ProjectPoolStatus[]
  data: [number, number, number][]
}

export interface TrendSummary {
  days: string[]
  counts: number[]
  costs: number[]
}

export interface WorkoverAnalytics {
  kpis: AnalyticsKpis
  status_counts: StatusCount[]
  measure_distribution: NameValue[]
  heatmap: HeatmapSummary
  trend: TrendSummary
  measure_types: string[]
}
