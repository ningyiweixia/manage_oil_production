import { http, unwrap } from './http'
import type { PageResult, WorkoverProject } from '../types/workover'

export type ApprovalTaskScope = 'pending' | 'processed' | 'rejected' | 'approved'
export type ApprovalActionCode = 'APPROVE' | 'REJECT' | 'RESUBMIT'

export interface ApprovalTaskQuery {
  scope?: ApprovalTaskScope
  page?: number
  page_size?: number
  well_no?: string
}

export interface ApprovalTask {
  business_type: string
  business_id: number
  project: WorkoverProject
  current_node: string
  node_label: string
  allowed_actions: ApprovalActionCode[]
  can_process: boolean
  stay_hours: number
  measure_summary?: string
  last_comment?: string
}

export interface ApprovalTimelineItem {
  id: number
  business_type: string
  business_id: number
  node_code: string
  node_label: string
  action: string
  action_label: string
  comment?: string
  operator_id?: number
  operator_name?: string
  before_status?: string
  after_status?: string
  created_at: string
}

function compactQuery<T extends object>(query: T) {
  return Object.fromEntries(
    Object.entries(query).filter(([, value]) => value !== '' && value !== undefined && value !== null)
  )
}

export async function listApprovalTasks(query: ApprovalTaskQuery): Promise<PageResult<ApprovalTask>> {
  return unwrap<PageResult<ApprovalTask>>(http.get('/approvals/tasks', { params: compactQuery(query) }))
}

export async function processProjectApproval(projectId: number, payload: { action: ApprovalActionCode; comment?: string }): Promise<WorkoverProject> {
  return unwrap<WorkoverProject>(http.patch(`/approvals/workover-project-pools/${projectId}`, payload))
}

export async function getApprovalTimeline(businessType: string, businessId: number): Promise<ApprovalTimelineItem[]> {
  return unwrap<ApprovalTimelineItem[]>(http.get(`/approvals/${businessType}/${businessId}/timeline`))
}
