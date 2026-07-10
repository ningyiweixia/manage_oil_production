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
import { getCurrentUser, type MenuNode } from '../api/auth'
import { clearSessionMenus, loadCachedMenus, refreshSessionMenus } from '../utils/menuCache'

const iconMap: Record<string, any> = {
  Tickets, TrendCharts, Setting, Monitor, Document, DataAnalysis, Bell, User,
  settings: Setting, database: DataAnalysis, table: Tickets, tickets: Tickets, team: OfficeBuilding,
  list: List, send: Promotion, edit: Edit, key: Key, menu: Menu, goods: List, truck: Promotion,
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
  '/workover/operation-sheets': Document,
  '/contractor/capacity': OfficeBuilding,
  '/contractor/dispatch': Promotion,
  '/contractor/operation-sheets': Document,
  '/material/requirements': List,
  '/material/delivery': Promotion,
  '/completion': Document,
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
const cachedMenus = ref<MenuNode[]>(loadCachedMenus())
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
    if (
      item.route_name === 'engineering'
      || item.route_name === 'engineering_designs'
      || item.route_path?.startsWith('/engineering')
      || item.route_name === 'contractor_sheets'
      || item.route_path === '/contractor/operation-sheets'
    ) {
      return []
    }
    const children = normalizeDeprecatedMenus(item.children || [])
    if (item.route_name === 'contractor' || item.route_path === '/contractor') {
      return children
        .filter((child) => child.route_name === 'contractor_capacity' || child.route_name === 'contractor_dispatch')
        .map((child) => normalizeCoreMenuOrder({ ...child, parent_id: null }))
    }
    if (item.route_name === 'workover' || item.route_path === '/workover') {
      return children.map((child) => ({
        ...child,
        parent_id: null,
        sort_order: child.route_name === 'workover_project_pool' ? item.sort_order : child.sort_order
      }))
    }
    return [normalizeCoreMenuOrder({ ...item, children })]
  })
}

function normalizeCoreMenuOrder(item: MenuNode): MenuNode {
  if (item.route_name === 'contractor_capacity' || item.route_path === '/contractor/capacity') {
    return { ...item, parent_id: null, sort_order: 22 }
  }
  if (item.route_name === 'contractor_dispatch' || item.route_path === '/contractor/dispatch') {
    return { ...item, parent_id: null, sort_order: 23 }
  }
  if (item.route_name === 'workover_operation' || item.route_path === '/workover/operation-sheets') {
    return { ...item, parent_id: null, sort_order: 24 }
  }
  return item
}

const workoverOperationMenu: MenuNode = {
  id: -3001,
  title: '修井运行管理',
  route_name: 'workover_operation',
  route_path: '/workover/operation-sheets',
  component: null,
  icon: 'document',
  parent_id: null,
  sort_order: 24,
  is_visible: true,
  is_active: true,
  meta: {},
  children: []
}

function hasMenuPath(items: MenuNode[], routePath: string): boolean {
  return items.some((item) => item.route_path === routePath || hasMenuPath(item.children || [], routePath))
}

function withWorkoverOperationMenu(items: MenuNode[]): MenuNode[] {
  if (hasMenuPath(items, '/workover/operation-sheets')) return items
  const canSeeOperation = permissions.value.includes('workover_operation:read') || permissions.value.includes('operation-sheet:read')
  if (!canSeeOperation) return items
  return [...items, workoverOperationMenu].sort((a, b) => a.sort_order - b.sort_order)
}

const systemSupportMenu: MenuNode = {
  id: -3002,
  title: '基础支撑',
  route_name: 'system_support',
  route_path: '/system/support',
  component: null,
  icon: 'monitor',
  parent_id: null,
  sort_order: 18,
  is_visible: true,
  is_active: true,
  meta: {},
  children: []
}

function canSeeSystemSupport() {
  const roles = Array.isArray((user.value as any)?.roles) ? (user.value as any).roles : []
  return permissions.value.includes('system:support:read')
    || Boolean((user.value as any)?.is_superuser)
    || roles.some((role: any) => role?.code === 'super_admin' || role?.code === 'ops_admin')
}

function withSystemSupportMenu(items: MenuNode[]): MenuNode[] {
  if (hasMenuPath(items, '/system/support') || !canSeeSystemSupport()) return items
  return items.map((item) => {
    if (item.route_name !== 'system' && item.route_path !== '/system' && !item.route_path?.startsWith('/system')) return item
    const children = [...(item.children || []), { ...systemSupportMenu, parent_id: item.id }]
      .sort((a, b) => a.sort_order - b.sort_order)
    return { ...item, children }
  })
}

/** Build sidebar menus from backend RBAC menus, with a static fallback */
const sidebarMenus = computed<MenuNode[]>(() => {
  const stored = cachedMenus.value
  if (stored && stored.length) {
    // Filter invisible menus and recursively filter children
    const filterVisible = (items: MenuNode[]): MenuNode[] =>
      items
        .filter((m) => m.is_visible !== false && m.is_active !== false)
        .map((m) => ({ ...m, children: filterVisible(m.children || []) }))
        .sort((a, b) => a.sort_order - b.sort_order)
    return withWorkoverOperationMenu(withSystemSupportMenu(withAccountSettingsMenu(normalizeDeprecatedMenus(filterVisible(stored))))).sort((a, b) => a.sort_order - b.sort_order)
  }
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
      id: 3, title: '运力报备', route_name: 'contractor_capacity', route_path: '/contractor/capacity',
      component: null, icon: 'team', parent_id: null, sort_order: 22,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 32, title: '智能派工', route_name: 'contractor_dispatch', route_path: '/contractor/dispatch',
      component: null, icon: 'send', parent_id: null, sort_order: 23,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 31, title: '修井运行管理', route_name: 'workover_operation', route_path: '/workover/operation-sheets',
      component: null, icon: 'document', parent_id: null, sort_order: 24,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 4, title: '物料管理', route_name: 'material', route_path: '/material',
      component: null, icon: 'goods', parent_id: null, sort_order: 4,
      is_visible: true, is_active: true, meta: {}, children: [
        {
          id: 41, title: '物料需求', route_name: 'material_requirements', route_path: '/material/requirements',
          component: null, icon: 'list', parent_id: 4, sort_order: 1,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 42, title: '物料配送', route_name: 'material_delivery', route_path: '/material/delivery',
          component: null, icon: 'truck', parent_id: 4, sort_order: 2,
          is_visible: true, is_active: true, meta: {}, children: []
        }
      ]
    },
    {
      id: 6, title: '完井台账', route_name: 'completion', route_path: '/completion',
      component: null, icon: 'document', parent_id: null, sort_order: 5,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 7, title: 'A5 系统集成', route_name: 'a5', route_path: '/a5/integration',
      component: null, icon: 'Monitor', parent_id: null, sort_order: 6,
      is_visible: true, is_active: true, meta: {}, children: []
    },
    {
      id: 8, title: '系统管理', route_name: 'system_users', route_path: '/system/users',
      component: null, icon: 'Setting', parent_id: null, sort_order: 7,
      is_visible: true, is_active: true, meta: {}, children: [
        {
          id: 81, title: '账号设置', route_name: 'system_account', route_path: '/system/account',
          component: null, icon: 'user', parent_id: 8, sort_order: 1,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 82, title: '用户管理', route_name: 'system_users', route_path: '/system/users',
          component: null, icon: 'user', parent_id: 8, sort_order: 2,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 83, title: '角色管理', route_name: 'system_roles', route_path: '/system/roles',
          component: null, icon: 'shield', parent_id: 8, sort_order: 3,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 84, title: '菜单管理', route_name: 'system_menus', route_path: '/system/menus',
          component: null, icon: 'menu', parent_id: 8, sort_order: 4,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 85, title: '权限管理', route_name: 'system_permissions', route_path: '/system/permissions',
          component: null, icon: 'key', parent_id: 8, sort_order: 5,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 86, title: '操作日志', route_name: 'system_logs', route_path: '/system/operation-logs',
          component: null, icon: 'file-text', parent_id: 8, sort_order: 6,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 87, title: '数据字典', route_name: 'system_dictionaries', route_path: '/system/dictionaries',
          component: null, icon: 'list', parent_id: 8, sort_order: 7,
          is_visible: true, is_active: true, meta: {}, children: []
        },
        {
          id: 88, title: '基础支撑', route_name: 'system_support', route_path: '/system/support',
          component: null, icon: 'monitor', parent_id: 8, sort_order: 8,
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
  clearSessionMenus()
  router.push('/login')
}

async function refreshMenusFromServer() {
  try {
    const currentUser = await getCurrentUser()
    refreshSessionMenus(currentUser)
    cachedMenus.value = loadCachedMenus()
  } catch {
    cachedMenus.value = loadCachedMenus()
  }
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
  void refreshMenusFromServer()
  connect()
  window.addEventListener('auth-expired', handleAuthExpired)
  window.addEventListener(PROJECT_NOTIFICATION, handleProjectNotification)
})

onBeforeUnmount(() => {
  window.removeEventListener('auth-expired', handleAuthExpired)
  window.removeEventListener(PROJECT_NOTIFICATION, handleProjectNotification)
})
</script>
