<template>
  <el-container class="app-shell">
    <el-aside width="232px" class="sidebar">
      <div class="brand">
        <strong>井下作业平台</strong>
        <span>采油二厂</span>
      </div>
      <el-menu router :default-active="$route.path" class="nav-menu">
        <el-menu-item index="/approval">
          <el-icon><Tickets /></el-icon>
          <span>审核审批工作台</span>
        </el-menu-item>
        <el-menu-item index="/dashboard">
          <el-icon><TrendCharts /></el-icon>
          <span>统计分析大屏</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="topbar">
        <div>
          <p>{{ route.meta.title }}</p>
        </div>
        <div class="topbar-actions">
          <el-popover placement="bottom-end" width="360" trigger="click" @show="notificationCount = 0">
            <template #reference>
              <el-badge :value="notificationCount" :hidden="notificationCount === 0">
                <el-button :icon="Bell" plain>待办通知</el-button>
              </el-badge>
            </template>
            <div class="notification-panel">
              <div class="notification-panel-head">
                <strong>通知记录</strong>
                <el-button text size="small" :disabled="!notifications.length" @click="clearNotifications">清空</el-button>
              </div>
              <el-empty v-if="!notifications.length" description="暂无通知" :image-size="72" />
              <div v-else class="notification-list">
                <button
                  v-for="item in notifications"
                  :key="item.id"
                  class="notification-item"
                  type="button"
                  @click="openNotification(item)"
                >
                  <strong>{{ item.title }}</strong>
                  <span>{{ item.message }}</span>
                  <small>{{ item.time }}</small>
                </button>
              </div>
            </div>
          </el-popover>
          <el-dropdown>
            <el-button :icon="User" circle />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>{{ user.full_name || user.username || '当前用户' }}</el-dropdown-item>
                <el-dropdown-item divided @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="content">
        <RouterView />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell, Tickets, TrendCharts, User } from '@element-plus/icons-vue'
import { useApprovalSocket } from '../composables/useApprovalSocket'
import { PROJECT_NOTIFICATION, type ProjectNotification } from '../composables/useProjectSync'
import { statusLabels } from '../utils/status'
import type { ProjectPoolStatus } from '../types/workover'

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

const route = useRoute()
const router = useRouter()
const { connect } = useApprovalSocket()
const notificationCount = ref(0)
const notifications = ref<Array<ProjectNotification & { id: number; title: string; message: string; time: string }>>([])
const user = computed(() => JSON.parse(localStorage.getItem('current_user') || '{}'))

function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  router.push('/login')
}

function handleAuthExpired() {
  router.push('/login')
}

function clearNotifications() {
  notifications.value = []
  notificationCount.value = 0
}

function openNotification(item: ProjectNotification) {
  router.push({
    path: '/approval',
    query: item.node_code ? { status: item.node_code } : undefined
  })
}

function notificationNodeLabel(payload: ProjectNotification) {
  const code = payload.node_code as ProjectPoolStatus | undefined
  return payload.node_label || (code ? notificationNodeLabels[code] || statusLabels[code] : '') || '待处理'
}

function notificationMessage(payload: ProjectNotification) {
  const code = payload.node_code as ProjectPoolStatus | undefined
  const message = payload.message || (code && notificationMessages[code]) || `收到新的审批消息：${notificationNodeLabel(payload)}`
  return String(message)
    .replaceAll('已流转至 已通过', '已通过审批，进入运行库')
    .replaceAll('已流转至已通过', '已通过审批，进入运行库')
    .replaceAll('流转至 已通过', '通过审批，进入运行库')
    .replaceAll('流转至已通过', '通过审批，进入运行库')
}

function handleProjectNotification(event: Event) {
  const payload = (event as CustomEvent<ProjectNotification>).detail || {}
  notificationCount.value += 1
  notifications.value.unshift({
    ...payload,
    id: Date.now() + Math.random(),
    title: payload.title || '审批待办提醒',
    message: notificationMessage(payload),
    time: new Date().toLocaleString('zh-CN', { hour12: false })
  })
  notifications.value = notifications.value.slice(0, 20)
}

onMounted(() => {
  connect()
  window.addEventListener('auth-expired', handleAuthExpired)
  window.addEventListener(PROJECT_NOTIFICATION, handleProjectNotification)
})

onBeforeUnmount(() => {
  window.removeEventListener('auth-expired', handleAuthExpired)
  window.removeEventListener(PROJECT_NOTIFICATION, handleProjectNotification)
})
</script>
