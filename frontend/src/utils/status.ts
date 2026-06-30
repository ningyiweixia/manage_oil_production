import type { ProjectPoolStatus } from '../types/workover'

export const statusLabels: Record<ProjectPoolStatus, string> = {
  DRAFT: '草稿',
  PENDING_GEOLOGY_VERIFY: '待地质核实',
  PENDING_PROCESS_VERIFY: '待工艺核实',
  APPROVED: '已入库',
  DISPATCHED: '已派工',
  REJECTED: '已驳回'
}

export const approvalStatusFlow: ProjectPoolStatus[] = [
  'DRAFT',
  'PENDING_GEOLOGY_VERIFY',
  'PENDING_PROCESS_VERIFY',
  'APPROVED',
  'DISPATCHED'
]

export const approvalFlowNodes = [
  { status: 'DRAFT', label: '提报' },
  { status: 'PENDING_GEOLOGY_VERIFY', label: '地质' },
  { status: 'PENDING_PROCESS_VERIFY', label: '工艺' },
  { status: 'APPROVED', label: '已入库' },
  { status: 'DISPATCHED', label: '已派工' }
] as const

const approvalProgressIndex: Record<ProjectPoolStatus, number> = {
  DRAFT: 0,
  PENDING_GEOLOGY_VERIFY: 1,
  PENDING_PROCESS_VERIFY: 2,
  APPROVED: 3,
  REJECTED: 1,
  DISPATCHED: 4
}

export function statusStep(status: ProjectPoolStatus) {
  const map: Record<ProjectPoolStatus, number> = {
    DRAFT: 0,
    PENDING_GEOLOGY_VERIFY: 1,
    PENDING_PROCESS_VERIFY: 2,
    APPROVED: 3,
    REJECTED: 1,
    DISPATCHED: 4
  }
  return map[status]
}

export function showApprovalFlow(status: ProjectPoolStatus) {
  return status !== 'REJECTED'
}

export function approvalNodeClass(status: ProjectPoolStatus, nodeStatus: ProjectPoolStatus, rejectedFrom?: ProjectPoolStatus | null) {
  let effectiveStatus = status
  if (status === 'REJECTED' && rejectedFrom) {
    effectiveStatus = rejectedFrom
  }
  const currentIndex = approvalProgressIndex[effectiveStatus]
  const nodeIndex = approvalProgressIndex[nodeStatus]
  const rejected = status === 'REJECTED'
  const dispatchWaiting = status === 'APPROVED' && nodeStatus === 'DISPATCHED'
  const completedStatus = status === 'APPROVED' || status === 'DISPATCHED'
  return {
    'is-done': currentIndex > nodeIndex || (completedStatus && currentIndex === nodeIndex),
    'is-current': (currentIndex === nodeIndex && !rejected && !completedStatus) || dispatchWaiting,
    'is-rejected': currentIndex === nodeIndex && rejected,
    'is-pending': currentIndex < nodeIndex && !dispatchWaiting
  }
}

export function isRejectedStatus(status: ProjectPoolStatus) {
  return status === 'REJECTED'
}

export function rejectedAtLabel(rejectedFrom: ProjectPoolStatus | null | undefined): string {
  if (rejectedFrom === 'PENDING_GEOLOGY_VERIFY') return '地质驳回'
  if (rejectedFrom === 'PENDING_PROCESS_VERIFY') return '工艺驳回'
  return '已驳回'
}

export function statusTagType(status: ProjectPoolStatus) {
  if (status === 'APPROVED' || status === 'DISPATCHED') return 'success'
  if (status === 'REJECTED') return 'danger'
  if (status === 'PENDING_GEOLOGY_VERIFY' || status === 'PENDING_PROCESS_VERIFY') return 'warning'
  return 'info'
}

export function nextApprovedStatus(status: ProjectPoolStatus): ProjectPoolStatus {
  if (status === 'PENDING_GEOLOGY_VERIFY') return 'PENDING_PROCESS_VERIFY'
  if (status === 'PENDING_PROCESS_VERIFY') return 'APPROVED'
  return status
}

export function canApprove(status: ProjectPoolStatus) {
  return status === 'PENDING_GEOLOGY_VERIFY' || status === 'PENDING_PROCESS_VERIFY'
}
