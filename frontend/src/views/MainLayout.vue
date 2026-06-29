<template>
  <el-container class="app-shell">
    <el-aside width="232px" class="sidebar">
      <div class="brand">
        <strong>井下作业平台</strong>
        <span>采油二厂</span>
      </div>
      <el-menu router :default-active="$route.path" class="nav-menu">
        <template v-for="item in sidebarMenus" :key="item.id">
          <el-sub-menu v-if="item.children && item.children.length" :index="String(item.id)">
            <template #title>
              <el-icon><component :is="resolveMenuIcon(item)" /></el-icon>
              <span>{{ item.title }}</span>
            </template>
            <el-menu-item
              v-for="child in item.children"
              :key="child.id"
              :index="child.route_path || String(child.id)"
            >
              <el-icon><component :is="resolveMenuIcon(child)" /></el-icon>
              <span>{{ child.title }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="item.route_path || String(item.id)">
            <el-icon><component :is="resolveMenuIcon(item)" /></el-icon>
            <span>{{ item.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container class="main-region">
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
                <el-dropdown-item @click="openAccountSettings">{{ user.full_name || user.username || '当前用户' }}</el-dropdown-item>
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
import { Bell, Tickets, TrendCharts, User, Setting, Monitor, Document, DataAnalysis, Edit, List, Key, Menu, OfficeBuilding, Promotion, Files } from '@element-plus/icons-vue'
import { useApprovalSocket } from '../composables/useApprovalSocket'
import { PROJECT_NOTIFICATION, normalizeNotificationMessage, type ProjectNotification } from '../composables/useProjectSync'
import type { MenuNode } from '../api/auth'

const iconMap: Record<string, any> = {
  Tickets, TrendCharts, Setting, Monitor, Document, DataAnalysis, Bell, User,
  settings: Setting, database: DataAnalysis, table: Tickets, team: OfficeBuilding,
  list: List, send: Promotion, edit: Edit, key: Key, menu: Menu,
  user: User, shield: Key, document: Document, monitor: Monitor, 'file-text': Files,
  'trend-charts': TrendCharts
}

const routeIconMap: Record<string, any> = {
  '/system/account': User,
  '/system/users': User,
  '/system/roles': Key,
  '/system/menus': Menu,
  '/system/permissions': Key,
  '/system/dictionaries': List,
  '/system/operation-logs': Files,
  '/workover/project-pools': Tickets,
  '/contractor/capacity': OfficeBuilding,
  '/contractor/dispatch': Promotion,
  '/contractor/operation-sheets': Document,
  '/engineering/designs': Edit,
  '/a5/integration': Monitor,
  '/dashboard': TrendCharts,
  '/approval': Tickets
}

function resolveMenuIcon(menu: MenuNode) {
  return (menu.icon && iconMap[menu.icon]) || (menu.route_path && routeIconMap[menu.route_path]) || Document
}

const route = useRoute()
const router = useRouter()
const { connect } = useApprovalSocket()
const notificationCount = ref(0)
const notifications = ref<Array<ProjectNotification & { id: number; title: string; message: string; time: string }>>([])
const user = computed(() => {
  try { return JSON.parse(localStorage.getItem('current_user') || '{}') } catch { return {} }
})
const permissions = computed<string[]>(() => {
  try { return JSON.parse(localStorage.getItem('permissions') || '[]') } catch { return [] }
})

function withAccountSettingsMenu(items: MenuNode[]): MenuNode[] {
  return items.map((item) => {
    if (item.route_name !== 'system' && item.route_path !== '/system') return item
    const children = item.children || []
    if (children.some((child) => child.route_path === '/system/account')) return item
    return {
      ...item,
      children: [
        {
          id: -1001,
          title: '账号设置',
          route_name: 'system_account',
          route_path: '/system/account',
          component: null,
          icon: 'user',
          parent_id: item.id,
          sort_order: 0,
          is_visible: true,
          is_active: true,
          meta: {},
          children: []
        },
        ...children
      ]
    }
  })
}

function normalizeDeprecatedMenus(items: MenuNode[]): MenuNode[] {
  return items.flatMap((item) => {
    const children = normalizeDeprecatedMenus(item.children || [])
    if (item.route_name === 'workover' || item.route_path === '/workover') {
      return children.map((child) => ({
        ...child,
        parent_id: null,
        sort_order: child.route_name === 'workover_project_pool' ? item.sort_order : child.sort_order
      }))
    }
    return [{ ...item, children }]
  })
}

/** Build sidebar menus from backend RBAC menus, with a static fallback */
const sidebarMenus = computed<MenuNode[]>(() => {
  try {
    const stored = JSON.parse(localStorage.getItem('menus') || '[]') as MenuNode[]
    if (stored && stored.length) {
      // Filter invisible menus and recursively filter children
      const filterVisible = (items: MenuNode[]): MenuNode[] =>
        items
          .filter((m) => m.is_visible !== false && m.is_active !== false)
          .map((m) => ({ ...m, children: filterVisible(m.children || []) }))
          .sort((a, b) => a.sort_order - b.sort_order)
      return withAccountSettingsMenu(normalizeDeprecatedMenus(filterVisible(stored))).sort((a, b) => a.sort_order - b.sort_order)
    }
  } catch { /* fall through to fallback */ }
  return [
    {
      id: 1, title: '审核审批工作台', route_name: 'approval', route_path: '/approval',
      component: null, icon: 'Tickets', parent_id: null, sort_order: 1,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 2, title: '统计分析大屏', route_name: 'dashboard', route_path: '/dashboard',
      component: null, icon: 'TrendCharts', parent_id: null, sort_order: 2,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 3, title: '承包商调度', route_name: 'contractor_dispatch', route_path: '/contractor/dispatch',
      component: null, icon: 'team', parent_id: null, sort_order: 3,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 4, title: '工程设计管理', route_name: 'engineering_designs', route_path: '/engineering/designs',
      component: null, icon: 'Document', parent_id: null, sort_order: 4,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 5, title: 'A5 系统集成', route_name: 'a5', route_path: '/a5/integration',
      component: null, icon: 'Monitor', parent_id: null, sort_order: 5,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 6, title: '系统管理', route_name: 'system_users', route_path: '/system/users',
      component: null, icon: 'Setting', parent_id: null, sort_order: 6,
      is_visible: true, is_active: true, meta: {}, children: [
        {
          id: 61, title: '账号设置', route_name: 'system_account', route_path: '/system/account',
          component: null, icon: 'user', parent_id: 6, sort_order: 1,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 62, title: '用户管理', route_name: 'system_users', route_path: '/system/users',
          component: null, icon: 'user', parent_id: 6, sort_order: 2,
          is_visible: true, is_active: true, meta: {}, children: []
        }
      ]
    }
  ]
})

function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('current_user')
  localStorage.removeItem('permissions')
  localStorage.removeItem('menus')
  router.push('/login')
}

function openAccountSettings() {
  router.push('/system/account')
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

function handleProjectNotification(event: Event) {
  const payload = (event as CustomEvent<ProjectNotification>).detail || {}
  notificationCount.value += 1
  notifications.value.unshift({
    ...payload,
    id: Date.now() + Math.random(),
    title: payload.title || '审批待办提醒',
    message: normalizeNotificationMessage(payload),
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
