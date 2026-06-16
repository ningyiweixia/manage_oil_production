import { onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { emitProjectDataChanged, emitProjectNotification } from './useProjectSync'
import { statusLabels } from '../utils/status'
import type { ProjectPoolStatus } from '../types/workover'

const MAX_RECONNECT_ATTEMPTS = 6
const BASE_RECONNECT_DELAY_MS = 1000
const notificationNodeLabels: Partial<Record<ProjectPoolStatus, string>> = {
  APPROVED: '入运行库'
}
const notificationMessages: Partial<Record<ProjectPoolStatus, string>> = {
  DRAFT: '项目已退回草稿',
  PENDING_GEOLOGY_VERIFY: '项目已提交至地质核实',
  PENDING_PROCESS_VERIFY: '项目已流转至工艺核实',
  APPROVED: '项目已通过审批，进入运行库',
  REJECTED: '项目已驳回，待补充修改',
  DISPATCHED: '项目已派工',
  VOIDED: '项目已作废'
}

function nodeLabel(payload: Record<string, any>) {
  const code = payload.node_code as ProjectPoolStatus | undefined
  return payload.node_label || (code && (notificationNodeLabels[code] || statusLabels[code])) || '待处理'
}

function normalizeMessage(payload: Record<string, any>) {
  const code = payload.node_code as ProjectPoolStatus | undefined
  let message = payload.message || (code && notificationMessages[code]) || `收到新的审批消息：${nodeLabel(payload)}`
  Object.entries(statusLabels).forEach(([code, name]) => {
    message = String(message).replaceAll(code, name)
  })
  message = String(message)
    .replaceAll('已流转至 已通过', '已通过审批，进入运行库')
    .replaceAll('已流转至已通过', '已通过审批，进入运行库')
    .replaceAll('流转至 已通过', '通过审批，进入运行库')
    .replaceAll('流转至已通过', '通过审批，进入运行库')
  return message
}

export function useApprovalSocket() {
  const router = useRouter()
  let socket: WebSocket | null = null
  let timer: number | undefined
  let reconnectAttempts = 0
  let closedByOwner = false

  function scheduleReconnect() {
    if (closedByOwner || reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return
    const delay = Math.min(BASE_RECONNECT_DELAY_MS * 2 ** reconnectAttempts, 30000)
    reconnectAttempts += 1
    timer = window.setTimeout(connect, delay)
  }

  function connect() {
    if (socket && (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN)) return

    const token = localStorage.getItem('access_token')
    if (!token) return
    const base = import.meta.env.VITE_WS_BASE_URL || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/approval`

    try {
      socket = new WebSocket(base)
      socket.onopen = () => {
        reconnectAttempts = 0
        socket?.send(JSON.stringify({ type: 'auth', token }))
      }
      socket.onmessage = (event) => {
        let payload: Record<string, any>
        try {
          payload = JSON.parse(event.data || '{}')
        } catch {
          return
        }
        const message = normalizeMessage(payload)
        emitProjectNotification({ ...payload, message, node_label: nodeLabel(payload) })
        if (payload.node_code || payload.status || payload.project_ids?.length) {
          emitProjectDataChanged()
        }
        ElNotification({
          title: payload.title || '审批待办提醒',
          message,
          type: payload.type || 'info',
          duration: 5000,
          onClick: () => {
            router.push({
              path: '/approval',
              query: payload.node_code ? { status: payload.node_code } : undefined
            })
          }
        })
      }
      socket.onclose = scheduleReconnect
      socket.onerror = () => socket?.close()
    } catch {
      scheduleReconnect()
    }
  }

  onBeforeUnmount(() => {
    closedByOwner = true
    if (timer) window.clearTimeout(timer)
    socket?.close()
  })

  return { connect }
}
