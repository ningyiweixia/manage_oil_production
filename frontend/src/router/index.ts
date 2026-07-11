import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../views/MainLayout.vue'
import LoginView from '../views/LoginView.vue'
import ApprovalWorkbench from '../views/ApprovalWorkbench.vue'
import ProjectPoolLedgerView from '../views/ProjectPoolLedgerView.vue'
import AnalyticsDashboard from '../views/AnalyticsDashboard.vue'
import ContractorDispatchView from '../views/ContractorDispatchView.vue'
import WorkoverOperationManageView from '../views/WorkoverOperationManageView.vue'
import A5IntegrationView from '../views/A5IntegrationView.vue'
import SystemAdminView from '../views/SystemAdminView.vue'
import MaterialManageView from '../views/MaterialManageView.vue'
import CompletionLedgerView from '../views/CompletionLedgerView.vue'
import { clearSessionMenus } from '../utils/menuCache'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView },
    {
      path: '/',
      component: MainLayout,
      redirect: '/approval',
      children: [
        { path: 'approval', component: ApprovalWorkbench, meta: { title: '审核审批工作台' } },
        { path: 'dashboard', component: AnalyticsDashboard, meta: { title: '统计分析大屏' } },
        { path: '/workover/project-pools', component: ProjectPoolLedgerView, meta: { title: '上修项目池台账' } },
        { path: '/workover/operation-sheets', component: WorkoverOperationManageView, meta: { title: '修井运行管理' } },
        { path: '/contractor/capacity', component: ContractorDispatchView, meta: { title: '承包商运力报备' } },
        { path: '/contractor/dispatch', component: ContractorDispatchView, meta: { title: '承包商运力报备' } },
        { path: '/contractor/operation-sheets', component: WorkoverOperationManageView, meta: { title: '修井运行管理' } },
        { path: '/material/requirements', component: MaterialManageView, meta: { title: '物料需求台账' } },
        { path: '/material/delivery', component: MaterialManageView, meta: { title: '物料配送跟踪' } },
        { path: '/completion', component: CompletionLedgerView, meta: { title: '完井分类台账' } },
        { path: '/a5/integration', component: A5IntegrationView, meta: { title: 'A5 系统集成' } },
        { path: '/system/account', component: SystemAdminView, meta: { title: '账号设置' } },
        { path: '/system/users', component: SystemAdminView, meta: { title: '系统用户管理' } },
        { path: '/system/roles', component: SystemAdminView, meta: { title: '系统角色管理' } },
        { path: '/system/menus', component: SystemAdminView, meta: { title: '系统菜单管理' } },
        { path: '/system/permissions', component: SystemAdminView, meta: { title: '系统权限管理' } },
        { path: '/system/operation-logs', component: SystemAdminView, meta: { title: '操作日志' } },
        { path: '/system/dictionaries', component: SystemAdminView, meta: { title: '数据字典管理' } },
        { path: '/system/support', component: SystemAdminView, meta: { title: '基础支撑' } }
      ]
    }
  ]
})

function isTokenValid(token: string | null): boolean {
  if (!token) return false
  const [, payload] = token.split('.')
  if (!payload) return false
  try {
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(payload.length / 4) * 4, '=')
    const decoded = JSON.parse(window.atob(normalized))
    return typeof decoded.exp === 'number' && decoded.exp * 1000 > Date.now()
  } catch {
    return false
  }
}

router.beforeEach((to) => {
  if (to.path !== '/login' && !isTokenValid(localStorage.getItem('access_token'))) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('current_user')
    localStorage.removeItem('permissions')
    clearSessionMenus()
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && isTokenValid(localStorage.getItem('access_token'))) {
    return typeof to.query.redirect === 'string' ? to.query.redirect : '/approval'
  }
  return true
})

export default router
