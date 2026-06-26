<template>
  <section class="kpi-grid">
    <div class="kpi-card">
      <span>同步状态</span>
      <strong>{{ status.last_sync_status }}</strong>
      <small>{{ status.last_sync_message || '暂无同步记录' }}</small>
    </div>
    <div class="kpi-card">
      <span>今日同步</span>
      <strong>{{ status.sync_count_today }}</strong>
      <small>Celery 定时和手动触发合计</small>
    </div>
    <div class="kpi-card">
      <span>运行中</span>
      <strong>{{ status.is_running ? '是' : '否' }}</strong>
      <small>{{ status.last_sync_time || '未记录时间' }}</small>
    </div>
    <div class="kpi-card">
      <span>A5 入口</span>
      <strong>SSO</strong>
      <small>生成 5 分钟有效跳转令牌</small>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>A5 系统集成</h2>
        <p>查看同步状态、手动触发数据拉取，并生成单点登录跳转。</p>
      </div>
      <el-button type="primary" :loading="syncing" :icon="Refresh" @click="triggerSync">触发同步</el-button>
    </div>
    <el-descriptions border :column="2">
      <el-descriptions-item label="最近状态">{{ status.last_sync_status }}</el-descriptions-item>
      <el-descriptions-item label="最近时间">{{ status.last_sync_time || '-' }}</el-descriptions-item>
      <el-descriptions-item label="同步信息">{{ status.last_sync_message || '-' }}</el-descriptions-item>
      <el-descriptions-item label="今日次数">{{ status.sync_count_today }}</el-descriptions-item>
    </el-descriptions>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>单点登录跳转</h2>
        <p>为指定井号生成 A5 安全跳转地址。</p>
      </div>
    </div>
    <el-form :model="ssoForm" inline>
      <el-form-item label="井号">
        <el-input v-model="ssoForm.well_no" placeholder="输入井号" />
      </el-form-item>
      <el-form-item label="路径">
        <el-input v-model="ssoForm.redirect_path" placeholder="/workorder" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Link" @click="createToken">生成跳转</el-button>
      </el-form-item>
    </el-form>
    <el-alert v-if="ssoUrl" type="success" show-icon :closable="false" title="跳转地址已生成">
      <template #default>
        <el-link type="primary" :href="ssoUrl" target="_blank">{{ ssoUrl }}</el-link>
      </template>
    </el-alert>
  </section>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Link, Refresh } from '@element-plus/icons-vue'
import { createA5SsoToken, getA5SyncStatus, triggerA5Sync, type A5SyncStatus } from '../api/a5'

const syncing = ref(false)
const ssoUrl = ref('')
const status = reactive<A5SyncStatus>({
  last_sync_status: 'unknown',
  last_sync_message: '',
  sync_count_today: 0,
  is_running: false
})
const ssoForm = reactive({ well_no: '', redirect_path: '/workorder' })

async function loadStatus() {
  Object.assign(status, await getA5SyncStatus())
}

async function triggerSync() {
  syncing.value = true
  try {
    const result = await triggerA5Sync()
    ElMessage.success(result.message)
    await loadStatus()
  } finally {
    syncing.value = false
  }
}

async function createToken() {
  const result = await createA5SsoToken(ssoForm.well_no, ssoForm.redirect_path)
  ssoUrl.value = result.redirect_url
}

onMounted(loadStatus)
</script>
