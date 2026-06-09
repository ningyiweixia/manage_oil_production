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

router.beforeEach((to) => {
  if (to.path !== '/login' && !localStorage.getItem('access_token')) {
    return '/login'
  }
  return true
})

export default router
