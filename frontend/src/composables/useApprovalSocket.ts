import { onBeforeUnmount } from 'vue'
import { ElNotification } from 'element-plus'

export function useApprovalSocket() {
  let socket: WebSocket | null = null
  let timer: number | undefined

  function connect() {
    const token = localStorage.getItem('access_token')
    const base = import.meta.env.VITE_WS_BASE_URL || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/approval`

    try {
      socket = new WebSocket(token ? `${base}?token=${encodeURIComponent(token)}` : base)
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data || '{}')
        ElNotification({
          title: payload.title || '审批待办提醒',
          message: payload.message || `有新的待办到达：${payload.node_code || '待处理节点'}`,
          type: payload.type || 'info',
          duration: 5000
        })
      }
      socket.onclose = () => {
        timer = window.setTimeout(connect, 8000)
      }
    } catch {
      timer = window.setTimeout(connect, 8000)
    }
  }

  onBeforeUnmount(() => {
    if (timer) window.clearTimeout(timer)
    socket?.close()
  })

  return { connect }
}
