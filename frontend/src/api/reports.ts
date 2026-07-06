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

export function getDeliverySummary() {
  return unwrap<DeliverySummary>(http.get('/reports/delivery-summary'))
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
