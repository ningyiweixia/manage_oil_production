import type { ProjectPoolStatus } from '../types/workover'

export const statusLabels: Record<ProjectPoolStatus, string> = {
  DRAFT: '草稿',
  PENDING_GEOLOGY_VERIFY: '待地质核实',
  PENDING_PROCESS_VERIFY: '待工艺核实',
  APPROVED: '已通过',
  REJECTED: '已驳回',
  DISPATCHED: '已派工',
  VOIDED: '已作废'
}

export const approvalStatusFlow: ProjectPoolStatus[] = [
  'DRAFT',
  'PENDING_GEOLOGY_VERIFY',
  'PENDING_PROCESS_VERIFY',
  'APPROVED'
]

export function statusStep(status: ProjectPoolStatus) {
  const map: Record<ProjectPoolStatus, number> = {
    DRAFT: 0,
    PENDING_GEOLOGY_VERIFY: 1,
    PENDING_PROCESS_VERIFY: 2,
    APPROVED: 4,
    REJECTED: 1,
    DISPATCHED: 4,
    VOIDED: 0
  }
  return map[status]
}

export function nextApprovedStatus(status: ProjectPoolStatus): ProjectPoolStatus {
  if (status === 'PENDING_GEOLOGY_VERIFY') return 'PENDING_PROCESS_VERIFY'
  if (status === 'PENDING_PROCESS_VERIFY') return 'APPROVED'
  return status
}

export function canApprove(status: ProjectPoolStatus) {
  return status === 'PENDING_GEOLOGY_VERIFY' || status === 'PENDING_PROCESS_VERIFY'
}
