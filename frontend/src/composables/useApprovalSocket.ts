import { onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElNotification } from 'element-plus'
import { emitProjectNotification } from './useProjectSync'

const MAX_RECONNECT_ATTEMPTS = 6
const BASE_RECONNECT_DELAY_MS = 1000

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
        emitProjectNotification(payload)
        ElNotification({
          title: payload.title || 'Approval reminder',
          message: payload.message || `New approval item: ${payload.node_code || 'pending'}`,
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
