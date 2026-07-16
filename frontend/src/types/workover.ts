export type ProjectPoolStatus =
  | 'DRAFT'
  | 'PENDING_GEOLOGY_VERIFY'
  | 'PENDING_PROCESS_VERIFY'
  | 'APPROVED'
  | 'REJECTED'
  | 'DISPATCHED'

export interface WorkoverMeasure {
  measure_type: string
  process?: string
  construction_params: Record<string, unknown>
  duration_days?: number
  estimated_cost?: number
}

export interface WorkoverAttachment {
  name: string
  url: string
  content_type: string
  size: number
  category: string
  uploaded_by?: string
  uploaded_at?: string
}

export interface WorkoverProject {
  id: number
  well_no: string
  well_name?: string
  well_type?: string
  layer?: string
  fault_description?: string
  territory_unit?: string
  block_name?: string
  county?: string
  report_unit: string
  initiator_name?: string
  initiator_phone?: string
  production_priority: number
  geology_verified_daily_oil?: number | null
  geology_verified_at?: string | null
  process_well_condition?: string | null
  process_can_workover?: boolean | null
  process_verified_at?: string | null
  status: ProjectPoolStatus
  reason?: string
  reason_category?: string
  completeness_status?: 'INCOMPLETE' | 'COMPLETE' | 'NEEDS_SUPPLEMENT'
  data_source?: 'manual' | 'excel' | 'external'
  report_batch?: string
  photo_requirement?: string
  rejection_supplement?: string
  is_duplicate_well?: boolean
  related_project_ids?: number[]
  measures_jsonb: { measures?: WorkoverMeasure[] }
  photo_urls?: string[]
  attachments?: WorkoverAttachment[]
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
  report_unit?: string
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
