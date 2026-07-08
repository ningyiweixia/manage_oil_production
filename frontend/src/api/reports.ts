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
}

export interface StatisticsAnalysis {
  query: StatisticsAnalysisQuery
  report_key_data: {
    total_projects: number
    pending_approvals: number
    approval_rate: number
    estimated_cost: number
    measure_distribution: { name: string; value: number }[]
    status_counts: unknown[]
    trend: unknown
    fields: string[]
  }
  completion_classification: {
    total: number
    by_measure_type: { measure_type: string; count: number }[]
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
  }
  operation_efficiency: {
    total_sheets?: number
    dispatch_rate?: number
    completion_rate?: number
    team_workload?: { team_name: string; sheet_count: number }[]
    runtime_focus?: Record<string, number>
  }
  trace_sources: string[]
  report_outputs: string[]
}

function compactParams(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== '')
  )
}

export function getDeliverySummary() {
  return unwrap<DeliverySummary>(http.get('/reports/delivery-summary'))
}

export function getStatisticsAnalysis(query: StatisticsAnalysisQuery) {
  return unwrap<StatisticsAnalysis>(http.get('/reports/statistics-analysis', { params: compactParams(query) }))
}

export async function downloadReport(path: '/reports/delivery-summary.xlsx' | '/reports/delivery-summary.docx', filename: string) {
  const response = await http.get(path, { responseType: 'blob' })
  const blob = new Blob([response.data])
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = filename
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(link.href), 0)
}
