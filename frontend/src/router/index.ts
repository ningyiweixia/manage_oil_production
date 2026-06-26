import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../views/MainLayout.vue'
import LoginView from '../views/LoginView.vue'
import ApprovalWorkbench from '../views/ApprovalWorkbench.vue'
import AnalyticsDashboard from '../views/AnalyticsDashboard.vue'
import ContractorDispatchView from '../views/ContractorDispatchView.vue'
import EngineeringDesignView from '../views/EngineeringDesignView.vue'
import A5IntegrationView from '../views/A5IntegrationView.vue'
import SystemAdminView from '../views/SystemAdminView.vue'
import DictionaryManageView from '../views/DictionaryManageView.vue'

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
        { path: '/workover/project-pools', component: ApprovalWorkbench, meta: { title: '上修项目池台账' } },
        { path: '/contractor/capacity', component: ContractorDispatchView, meta: { title: '承包商运力报备' } },
        { path: '/contractor/dispatch', component: ContractorDispatchView, meta: { title: '智能派工' } },
        { path: '/contractor/operation-sheets', component: ContractorDispatchView, meta: { title: '修井运行表' } },
        { path: '/engineering/designs', component: EngineeringDesignView, meta: { title: '工程设计管理' } },
        { path: '/a5/integration', component: A5IntegrationView, meta: { title: 'A5 系统集成' } },
        { path: '/system/users', component: SystemAdminView, meta: { title: '系统用户管理' } },
        { path: '/system/roles', component: SystemAdminView, meta: { title: '系统角色管理' } },
        { path: '/system/menus', component: SystemAdminView, meta: { title: '系统菜单管理' } },
        { path: '/system/permissions', component: SystemAdminView, meta: { title: '系统权限管理' } },
        { path: '/system/operation-logs', component: SystemAdminView, meta: { title: '操作日志' } },
        { path: '/system/dictionaries', component: DictionaryManageView, meta: { title: '数据字典管理' } }
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
    localStorage.removeItem('menus')
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.path === '/login' && isTokenValid(localStorage.getItem('access_token'))) {
    return typeof to.query.redirect === 'string' ? to.query.redirect : '/approval'
  }
  return true
})

export default router
