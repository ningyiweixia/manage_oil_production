import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '../views/MainLayout.vue'
import LoginView from '../views/LoginView.vue'
import ApprovalWorkbench from '../views/ApprovalWorkbench.vue'
import AnalyticsDashboard from '../views/AnalyticsDashboard.vue'

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
        { path: 'dashboard', component: AnalyticsDashboard, meta: { title: '统计分析大屏' } }
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
