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
    <div class="kpi-card">
      <span>异常情况</span>
      <strong>{{ analytics.anomaly_total }}</strong>
      <small>A5 同步缓存统计</small>
    </div>
    <div class="kpi-card">
      <span>特殊工序</span>
      <strong>{{ analytics.special_process_total }}</strong>
      <small>按工序类别聚合</small>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>A5同步记录</h2>
        <p>持久化保留定时、手动和单工单日报同步结果。</p>
      </div>
    </div>
    <el-table :data="syncLogs" empty-text="暂无同步记录">
      <el-table-column prop="started_at" label="开始时间" min-width="170" />
      <el-table-column prop="sync_type" label="方式" width="100" />
      <el-table-column prop="requested_operation_no" label="作业编号" min-width="150" />
      <el-table-column prop="status" label="结果" width="100" />
      <el-table-column prop="total_count" label="总数" width="72" />
      <el-table-column prop="updated_count" label="更新" width="72" />
      <el-table-column prop="unchanged_count" label="未变" width="72" />
      <el-table-column prop="not_found_count" label="未匹配" width="82" />
      <el-table-column prop="failed_count" label="失败" width="72" />
      <el-table-column prop="error_message" label="失败原因" min-width="180" show-overflow-tooltip />
    </el-table>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>A5 系统集成</h2>
        <p>查看同步状态、手动触发数据拉取，并生成单点登录跳转。</p>
      </div>
      <div class="panel-actions">
        <el-button :icon="Download" @click="exportReport">导出报告</el-button>
        <el-button type="primary" :loading="syncing" :icon="Refresh" @click="triggerSync">触发同步</el-button>
      </div>
    </div>
    <el-form :model="analyticsQuery" inline>
      <el-form-item label="开始日期">
        <el-date-picker v-model="analyticsQuery.start_date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="analyticsQuery.end_date" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="类别">
        <el-input v-model="analyticsQuery.category" clearable placeholder="异常或工序类别" />
      </el-form-item>
      <el-form-item label="模板">
        <el-input v-model="analyticsQuery.template_name" clearable placeholder="默认统计模板" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadStatus">统计</el-button>
      </el-form-item>
    </el-form>
    <el-descriptions border :column="2">
      <el-descriptions-item label="最近状态">{{ status.last_sync_status }}</el-descriptions-item>
      <el-descriptions-item label="最近时间">{{ status.last_sync_time || '-' }}</el-descriptions-item>
      <el-descriptions-item label="同步信息">{{ status.last_sync_message || '-' }}</el-descriptions-item>
      <el-descriptions-item label="今日次数">{{ status.sync_count_today }}</el-descriptions-item>
      <el-descriptions-item label="接口模式">
        {{ status.adapter_mode === 'mock' ? '模拟接口' : '正式接口' }}
        <span v-if="status.adapter_mode === 'mock' && status.mock_scenario">（{{ status.mock_scenario }}）</span>
      </el-descriptions-item>
    </el-descriptions>
  </section>

  <section class="split-grid">
    <article class="table-panel">
      <div class="panel-head">
        <div>
          <h2>异常情况统计</h2>
          <p>按 A5 异常类别汇总。</p>
        </div>
      </div>
      <el-table :data="analytics.anomaly_distribution" row-key="name">
        <el-table-column prop="name" label="异常类别" min-width="160" />
        <el-table-column prop="value" label="数量" width="100" />
      </el-table>
    </article>
    <article class="table-panel">
      <div class="panel-head">
        <div>
          <h2>特殊工序统计</h2>
          <p>按 A5 工序类别汇总。</p>
        </div>
      </div>
      <el-table :data="analytics.process_distribution" row-key="name">
        <el-table-column prop="name" label="工序类别" min-width="160" />
        <el-table-column prop="value" label="数量" width="100" />
      </el-table>
    </article>
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
import { Download, Link, Refresh, Search } from '@element-plus/icons-vue'
import { createA5SsoToken, exportA5AnalyticsReport, getA5Analytics, getA5SyncStatus, listA5SyncLogs, triggerA5Sync, type A5Analytics, type A5SyncBatch, type A5SyncStatus } from '../api/a5'

const syncing = ref(false)
const ssoUrl = ref('')
const syncLogs = ref<A5SyncBatch[]>([])
const status = reactive<A5SyncStatus>({
  last_sync_status: 'unknown',
  last_sync_message: '',
  sync_count_today: 0,
  is_running: false,
  adapter_mode: 'mock',
  mock_scenario: null
})
const analytics = reactive<A5Analytics>({
  anomaly_total: 0,
  special_process_total: 0,
  anomaly_distribution: [],
  process_distribution: [],
  trend: {
    days: [],
    anomaly_counts: [],
    process_counts: []
  }
})
const analyticsQuery = reactive<{ start_date?: string; end_date?: string; category?: string; template_name?: string }>({})
const ssoForm = reactive({ well_no: '', redirect_path: '/workorder' })

async function loadStatus() {
  const [syncStatus, summary, logs] = await Promise.all([getA5SyncStatus(), getA5Analytics(compactQuery(analyticsQuery)), listA5SyncLogs()])
  Object.assign(status, syncStatus)
  Object.assign(analytics, summary)
  syncLogs.value = logs
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

function compactQuery<T extends object>(query: T) {
  return Object.fromEntries(Object.entries(query).filter(([, value]) => value !== '' && value !== undefined && value !== null))
}

async function exportReport() {
  const file = await exportA5AnalyticsReport(compactQuery(analyticsQuery))
  const binary = atob(file.content_base64)
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0))
  const url = URL.createObjectURL(new Blob([bytes], { type: file.content_type }))
  const link = document.createElement('a')
  link.href = url
  link.download = file.filename
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('报告已导出')
}

onMounted(loadStatus)
</script>
