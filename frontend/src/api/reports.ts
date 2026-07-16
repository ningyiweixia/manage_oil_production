import { http, unwrap } from './http'

export interface DeliverySummary {
  projects: {
    total: number
    pending_approvals: number
    approval_rate: number
    estimated_cost: number
  }
  operations: {
    total_sheets: number
    dispatch_rate: number
    completion_rate: number
    team_workload: { team_name: string; sheet_count: number }[]
  }
  materials: {
    total: number
    delivered: number
    arrived: number
    used: number
    emergency_count: number
  }
  completions: {
    total: number
    by_measure_type: { measure_type: string; count: number }[]
  }
  production_gain?: {
    effective_rate: number
    total_daily_oil_gain: number
    monthly_gain_tons: number
    avg_cost_per_ton: number
    pump_improved_rate: number
    by_measure_effect: { measure_type: string; count: number; effective_count: number; effective_rate: number; avg_oil_gain: number; cost_per_ton: number }[]
  }
}

export interface StatisticsAnalysisQuery {
  start_date?: string
  end_date?: string
  well_no?: string
  report_unit?: string
  measure_type?: string
  team_name?: string
  process_type?: string
  material_status?: string
  block_name?: string
  status?: string
  compare_type?: 'mom' | 'yoy' | 'wow' | 'none'
}

export interface KpiDelta {
  current: number
  previous: number
  change: number
  change_pct: number
}

export interface ComparisonResult {
  mode: string
  prev_period?: { start_date: string; end_date: string }
  deltas: Record<string, KpiDelta>
}

export interface ApprovalStageSummary {
  node: string
  avg_hours: number
  sample_count: number
  max_hours: number
}

export interface ApprovalEfficiency {
  total_actions: number
  total_approvals: number
  total_rejections: number
  rejection_rate: number
  stage_summary: ApprovalStageSummary[]
  bottleneck: { node: string | null; avg_hours: number }
  top_reject_reasons: { reason: string; count: number }[]
  top_approvers: { operator_id: number; operator_name: string; approve_count: number; reject_count: number; total_actions: number }[]
}

export interface ContractorTeamScore {
  team_name: string
  completed_count: number
  effective_count: number
  total_oil_gain: number
  a5_anomaly_count: number
  effective_rate: number
  avg_oil_gain: number
  score: number
}

export interface MaterialTiming {
  avg_order_to_delivery_days: number
  avg_delivery_to_arrive_days: number
  avg_arrive_to_use_days: number
  on_time_delivery_rate: number
  on_time_count: number
  on_time_total: number
}

export interface StatisticsAnalysis {
  query: StatisticsAnalysisQuery
  overview_kpis: {
    total_projects: number
    pending_approvals: number
    approval_rate: number
    estimated_cost: number
    operation_sheets: number
    a5_anomalies: number
    material_requirements: number
    completion_records: number
    data_quality_issues?: number
    measure_effective_rate?: number
    total_daily_oil_gain?: number
    monthly_gain_tons?: number
    avg_cost_per_ton?: number
  }
  completion_classification: {
    total: number
    by_measure_type: { measure_type: string; count: number }[]
    production_gain?: {
      total_daily_oil_gain: number
      avg_daily_oil_gain: number
      monthly_gain_tons: number
      effective_count: number
      effective_rate: number
      pump_efficiency_avg_improvement: number
      pump_improved_count: number
      pump_improved_rate: number
      total_estimated_cost: number
      avg_cost_per_ton: number
    }
    by_measure_effect?: { measure_type: string; count: number; effective_count: number; effective_rate: number; avg_oil_gain: number; cost_per_ton: number }[]
  }
  data_quality_summary: {
    checked_at: string
    total_issues: number
    severity_counts: { high: number; medium: number; low: number }
    issues: {
      rule_code: string
      title: string
      severity: 'low' | 'medium' | 'high'
      message: string
      entity_type: string
      entity_id?: number | null
      well_no?: string | null
      team_name?: string | null
      suggestion?: string | null
    }[]
    scope: Record<string, unknown>
  }
  a5_statistics: {
    anomaly_total: number
    special_process_total: number
    anomaly_distribution: { name: string; value: number }[]
    process_distribution: { name: string; value: number }[]
    trend: unknown
  }
  material_usage: {
    total: number
    pending?: number
    approved?: number
    planned?: number
    delivered?: number
    arrived?: number
    used?: number
    canceled?: number
    emergency_count?: number
    exception_count?: number
    usage_rate?: number
    timing?: MaterialTiming
  }
  operation_efficiency: {
    total_sheets?: number
    dispatch_rate?: number
    completion_rate?: number
    team_workload?: { team_name: string; sheet_count: number }[]
    runtime_focus?: Record<string, number>
  }
  trace_sources: string[]
  comparison: ComparisonResult
  approval_efficiency: ApprovalEfficiency
  contractor_performance: ContractorTeamScore[]
  integration_status?: Record<string, unknown>
  chart_series: {
    approval_status: { name: string; value: number; status?: string }[]
    measure_distribution: { name: string; value: number }[]
    block_status_heatmap: { blocks: string[]; statuses: string[]; data: [number, number, number][] }
    submission_trend: { days: string[]; counts: number[]; costs: number[] }
    a5_anomaly_trend: { days: string[]; anomaly_counts: number[]; process_counts: number[] }
    material_status_distribution: { name: string; value: number }[]
    team_workload_rank: { team_name: string; sheet_count: number }[]
    completion_measure_distribution: { name: string; value: number }[]
    production_gain_by_measure?: { measure_type: string; count: number; effective_count: number; effective_rate: number; avg_oil_gain: number; cost_per_ton: number }[]
    production_gain_summary?: { total_daily_oil_gain: number; effective_rate: number; monthly_gain_tons: number; avg_cost_per_ton: number; pump_improved_rate: number }
    approval_stage_summary?: ApprovalStageSummary[]
    approval_bottleneck?: { node: string | null; avg_hours: number }
    contractor_performance_scores?: ContractorTeamScore[]
  }
  report_outputs: string[]
}

function compactParams(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '')
  )
}

function nameValue(items?: Array<{ name?: string; label?: string; count?: number; value?: number }>) {
  return (items || []).map((item) => ({
    name: item.name || item.label || '',
    value: Number(item.value ?? item.count ?? 0)
  }))
}

function statusNameValue(items?: Array<{ status?: string; label?: string; count?: number; value?: number }>) {
  return (items || []).map((item) => ({
    name: item.label || item.status || '',
    value: Number(item.value ?? item.count ?? 0),
    status: item.status
  }))
}

export function normalizeStatisticsAnalysis(payload: any): StatisticsAnalysis {
  if (payload?.overview_kpis && payload?.chart_series && payload?.data_quality_summary) {
    return payload as StatisticsAnalysis
  }

  const report_key_data = payload?.report_key_data || {}
  const material = payload?.material_usage || {}
  const completion = payload?.completion_classification || { total: 0, by_measure_type: [] }
  const a5 = payload?.a5_statistics || { anomaly_total: 0, special_process_total: 0, trend: { days: [], anomaly_counts: [], process_counts: [] } }
  const operation = payload?.operation_efficiency || {}

  return {
    query: payload?.query || {},
    overview_kpis: {
      total_projects: Number(report_key_data.total_projects || 0),
      pending_approvals: Number(report_key_data.pending_approvals || 0),
      approval_rate: Number(report_key_data.approval_rate || 0),
      estimated_cost: Number(report_key_data.estimated_cost || 0),
      operation_sheets: Number(operation.total_sheets || 0),
      a5_anomalies: Number(a5.anomaly_total || 0),
      material_requirements: Number(material.total || 0),
      completion_records: Number(completion.total || 0),
      data_quality_issues: payload?.data_quality_summary?.total_issues ?? 0,
      measure_effective_rate: payload?.overview_kpis?.measure_effective_rate ?? payload?.production_gain?.effective_rate ?? 0,
      total_daily_oil_gain: payload?.overview_kpis?.total_daily_oil_gain ?? payload?.production_gain?.total_daily_oil_gain ?? 0,
      monthly_gain_tons: payload?.overview_kpis?.monthly_gain_tons ?? payload?.production_gain?.monthly_gain_tons ?? 0,
      avg_cost_per_ton: payload?.overview_kpis?.avg_cost_per_ton ?? payload?.production_gain?.avg_cost_per_ton ?? 0,
    },
    completion_classification: completion,
    data_quality_summary: payload?.data_quality_summary || {
      checked_at: new Date().toISOString(),
      total_issues: 0,
      severity_counts: { high: 0, medium: 0, low: 0 },
      issues: [],
      scope: {}
    },
    a5_statistics: a5,
    material_usage: material,
    operation_efficiency: operation,
    trace_sources: payload?.trace_sources || [],
    comparison: payload?.comparison || { mode: 'none', deltas: {} },
    approval_efficiency: payload?.approval_efficiency || {
      total_actions: 0, total_approvals: 0, total_rejections: 0,
      rejection_rate: 0, stage_summary: [],
      bottleneck: { node: null, avg_hours: 0 },
      top_reject_reasons: [], top_approvers: []
    },
    contractor_performance: payload?.contractor_performance || [],
    chart_series: {
      approval_status: statusNameValue(report_key_data.status_counts),
      measure_distribution: nameValue(report_key_data.measure_distribution),
      block_status_heatmap: report_key_data.heatmap || { blocks: [], statuses: [], data: [] },
      submission_trend: report_key_data.trend || { days: [], counts: [], costs: [] },
      a5_anomaly_trend: a5.trend || { days: [], anomaly_counts: [], process_counts: [] },
      material_status_distribution: nameValue(material.status_distribution),
      team_workload_rank: operation.team_workload || [],
      completion_measure_distribution: (completion.by_measure_type || []).map((item: any) => ({
        name: item.measure_type,
        value: Number(item.count || 0)
      }))
    },
    report_outputs: payload?.report_outputs || []
  }
}

export function getDeliverySummary() {
  return unwrap<DeliverySummary>(http.get('/reports/delivery-summary'))
}

export function getStatisticsAnalysis(query: StatisticsAnalysisQuery) {
  return unwrap<any>(http.get('/reports/statistics-analysis', { params: compactParams(query) })).then(normalizeStatisticsAnalysis)
}

export async function downloadReport(
  path:
    | '/reports/delivery-summary.xlsx'
    | '/reports/delivery-summary.docx'
    | '/reports/statistics-analysis.xlsx'
    | '/reports/statistics-analysis.docx',
  filename: string,
  params?: StatisticsAnalysisQuery
) {
  const response = await http.get(path, { responseType: 'blob', params: params ? compactParams(params) : undefined })
  const blob = new Blob([response.data])
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(link.href), 0)
}

export function downloadStatisticsAnalysisExcel(query: StatisticsAnalysisQuery) {
  return downloadReport('/reports/statistics-analysis.xlsx', '数据统计分析.xlsx', query)
}

export function downloadStatisticsAnalysisWord(query: StatisticsAnalysisQuery) {
  return downloadReport('/reports/statistics-analysis.docx', '数据统计分析.docx', query)
}
