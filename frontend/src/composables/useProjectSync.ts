import { onBeforeUnmount, onMounted } from 'vue'
import { statusLabels } from '../utils/status'
import type { ProjectPoolStatus } from '../types/workover'

export const PROJECT_DATA_CHANGED = 'project-data-changed'
export const PROJECT_NOTIFICATION = 'project-notification'

export interface ProjectNotification {
  title?: string
  message?: string
  node_code?: string
  node_label?: string
  status?: string
  project_ids?: number[]
}

/** Shared map for labeling approval nodes, used across MainLayout and useApprovalSocket */
export const notificationNodeLabels: Partial<Record<ProjectPoolStatus, string>> = {
  APPROVED: '入运行库'
}

/** Shared message templates for each approval status */
export const notificationMessages: Partial<Record<ProjectPoolStatus, string>> = {
  DRAFT: '项目已退回草稿',
  PENDING_GEOLOGY_VERIFY: '项目已提交至地质核实',
  PENDING_PROCESS_VERIFY: '项目已流转至工艺核实',
  APPROVED: '项目已通过审批，进入运行库',
  REJECTED: '项目已驳回，待补充修改',
  DISPATCHED: '项目已派工',
  VOIDED: '项目已作废'
}

/** Resolve a human-readable node label from a WebSocket/notification payload */
export function resolveNodeLabel(payload: Record<string, any>): string {
  const code = payload.node_code as ProjectPoolStatus | undefined
  return payload.node_label || (code ? notificationNodeLabels[code] || statusLabels[code] : '') || '待处理'
}

/** Normalize a notification message string — clean up duplicated status phrases */
export function normalizeNotificationMessage(payload: Record<string, any>): string {
  const code = payload.node_code as ProjectPoolStatus | undefined
  let message = payload.message || (code && notificationMessages[code]) || `收到新的审批消息：${resolveNodeLabel(payload)}`
  // Replace status codes with Chinese labels
  Object.entries(statusLabels).forEach(([codeVal, name]) => {
    message = String(message).replaceAll(codeVal, name)
  })
  // Clean up cascaded phrases caused by label replacement
  message = String(message)
    .replaceAll('已流转至 已通过', '已通过审批，进入运行库')
    .replaceAll('已流转至已通过', '已通过审批，进入运行库')
    .replaceAll('流转至 已通过', '通过审批，进入运行库')
    .replaceAll('流转至已通过', '通过审批，进入运行库')
  return message
}

export function emitProjectDataChanged() {
  window.dispatchEvent(new CustomEvent(PROJECT_DATA_CHANGED))
}

export function emitProjectNotification(payload: ProjectNotification) {
  window.dispatchEvent(new CustomEvent(PROJECT_NOTIFICATION, { detail: payload }))
}

export function useProjectDataChanged(callback: () => void) {
  onMounted(() => window.addEventListener(PROJECT_DATA_CHANGED, callback))
  onBeforeUnmount(() => window.removeEventListener(PROJECT_DATA_CHANGED, callback))
}
