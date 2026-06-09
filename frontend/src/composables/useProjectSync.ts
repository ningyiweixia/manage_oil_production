import { onBeforeUnmount, onMounted } from 'vue'

export const PROJECT_DATA_CHANGED = 'project-data-changed'
export const PROJECT_NOTIFICATION = 'project-notification'

export interface ProjectNotification {
  title?: string
  message?: string
  node_code?: string
  status?: string
  project_ids?: number[]
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
