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
          <small>Vue 3 + Element Plus + ECharts</small>
        </div>
        <div class="topbar-actions">
          <el-tag type="success" effect="plain">WebSocket 待办监听</el-tag>
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
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Tickets, TrendCharts, User } from '@element-plus/icons-vue'
import { useApprovalSocket } from '../composables/useApprovalSocket'

const route = useRoute()
const router = useRouter()
const { connect } = useApprovalSocket()
const user = computed(() => JSON.parse(localStorage.getItem('current_user') || '{}'))

function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  router.push('/login')
}

onMounted(connect)
</script>
