<template>
  <section class="toolbar">
    <el-form :model="query" inline>
      <el-form-item label="运行状态">
        <el-select v-model="query.status" clearable placeholder="全部状态" style="width: 160px" @change="loadData">
          <el-option label="待运行" value="WAITING_DISPATCH" />
          <el-option label="已派工" value="DISPATCHED" />
          <el-option label="施工中" value="WORKING" />
          <el-option label="已完工" value="FINISHED" />
          <el-option label="已取消" value="CANCELED" />
        </el-select>
      </el-form-item>
      <el-form-item label="项目ID">
        <el-input-number v-model="query.project_id" :min="1" clearable />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadData">查询</el-button>
        <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="stats-bar">
    <div class="stats-card">
      <span class="stats-label">运行表总数</span>
      <strong class="stats-value">{{ dashboard?.total_sheets || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">待运行</span>
      <strong class="stats-value warn">{{ dashboard?.runtime_focus?.waiting || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">施工中</span>
      <strong class="stats-value primary">{{ dashboard?.runtime_focus?.working || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">已完工</span>
      <strong class="stats-value success">{{ dashboard?.runtime_focus?.finished || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">A5同步</span>
      <strong class="stats-value">{{ dashboard?.runtime_focus?.a5_synced || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">完井记录</span>
      <strong class="stats-value">{{ dashboard?.runtime_focus?.completion_total || 0 }}</strong>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>修井运行管理</h2>
        <p>跟踪审批入库后的运行表、施工进度、A5同步、物料状态和完井状态。</p>
      </div>
      <el-button :icon="Refresh" @click="loadPriority">刷新待运行</el-button>
    </div>
    <el-table v-loading="loading" :data="sheets" row-key="id" empty-text="暂无运行表">
      <el-table-column prop="operation_no" label="作业编号" min-width="180" fixed />
      <el-table-column prop="project_id" label="项目ID" width="90" />
      <el-table-column label="状态" width="115">
        <template #default="{ row }">
          <el-tag :type="sheetTag(row.status)">{{ sheetStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" min-width="160">
        <template #default="{ row }">
          <el-progress :percentage="row.progress" />
        </template>
      </el-table-column>
      <el-table-column label="闭环状态" min-width="260">
        <template #default="{ row }">
          <div class="closed-loop-cell">
            <el-tag :type="closedLoopTag(row.closed_loop_status?.overall)" effect="dark">
              {{ closedLoopLabel(row.closed_loop_status?.overall) }}
            </el-tag>
            <span class="muted-text">
              {{ row.closed_loop_status?.done_count || 0 }}/{{ row.closed_loop_status?.total_count || 5 }}
            </span>
            <div class="closed-loop-stages">
              <el-tag
                v-for="stage in row.closed_loop_status?.stages || []"
                :key="stage.key"
                :type="stage.done ? 'success' : 'info'"
                size="small"
                effect="plain"
              >
                {{ stage.label }}
              </el-tag>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="物料状态" min-width="140">
        <template #default="{ row }">
          <el-tag :type="materialTag(row.material_status?.status)" effect="plain">
            {{ materialStatusLabel(row.material_status?.status) }}
          </el-tag>
          <span class="muted-text material-count">共 {{ row.material_status?.total || 0 }} 项</span>
        </template>
      </el-table-column>
      <el-table-column label="完井状态" min-width="120">
        <template #default="{ row }">
          <el-tag :type="row.completion_status?.status === 'RECORDED' ? 'success' : 'info'" effect="plain">
            {{ row.completion_status?.status === 'RECORDED' ? '已登记' : '未登记' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="A5同步" min-width="130">
        <template #default="{ row }">
          <el-tag v-if="row.a5_status" effect="plain">{{ row.a5_status }}</el-tag>
          <span v-else class="muted-text">未同步</span>
        </template>
      </el-table-column>
      <el-table-column prop="a5_remark" label="A5备注" min-width="160" show-overflow-tooltip />
      <el-table-column label="更新时间" min-width="170">
        <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="openProgress(row)">更新进度</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-model:current-page="query.page"
      v-model:page-size="query.page_size"
      class="pager"
      layout="total, sizes, prev, pager, next"
      :total="total"
      @change="loadData"
    />
  </section>

  <el-dialog v-model="progressVisible" title="更新进度" width="480px">
    <el-form label-position="top">
      <el-form-item label="施工进度">
        <el-slider v-model="progressValue" :max="100" show-input />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="progressRemark" type="textarea" :rows="3" placeholder="填写现场进展、异常或交接说明" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="progressVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveProgress">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import {
  getWorkoverOperationDashboard,
  listPriorityWorkoverOperationSheets,
  listWorkoverOperationSheets,
  updateWorkoverOperationProgress,
  type ManagedOperationSheet,
  type OperationDashboard
} from '../api/workoverOperation'
import type { OperationSheetQuery, OperationStatus } from '../api/contractor'

const sheetStatusText: Record<OperationStatus, string> = {
  WAITING_DISPATCH: '待运行',
  DISPATCHED: '已派工',
  WORKING: '施工中',
  FINISHED: '已完工',
  CANCELED: '已取消'
}
const materialStatusText: Record<string, string> = {
  NONE: '无需求',
  PENDING: '待处理',
  APPROVED: '已审核',
  PLANNED: '已计划',
  DELIVERED: '已出库',
  ARRIVED: '已到场',
  USED: '已使用',
  CANCELED: '已取消'
}

const loading = ref(false)
const saving = ref(false)
const sheets = ref<ManagedOperationSheet[]>([])
const total = ref(0)
const dashboard = ref<OperationDashboard | null>(null)
const progressVisible = ref(false)
const progressTarget = ref<ManagedOperationSheet | null>(null)
const progressValue = ref(0)
const progressRemark = ref('')
const query = reactive<OperationSheetQuery>({ page: 1, page_size: 10, status: '' })

function sheetStatusLabel(status: OperationStatus) {
  return sheetStatusText[status] || status
}

function sheetTag(status: OperationStatus) {
  if (status === 'FINISHED') return 'success'
  if (status === 'CANCELED') return 'danger'
  if (status === 'WAITING_DISPATCH') return 'warning'
  return 'primary'
}

function materialStatusLabel(status?: string) {
  return materialStatusText[status || 'NONE'] || status || '无需求'
}

function materialTag(status?: string) {
  if (status === 'USED' || status === 'ARRIVED') return 'success'
  if (status === 'DELIVERED' || status === 'PLANNED') return 'primary'
  if (status === 'PENDING' || status === 'APPROVED') return 'warning'
  if (status === 'CANCELED') return 'danger'
  return 'info'
}

function closedLoopLabel(status?: string) {
  if (status === 'COMPLETE') return '已闭环'
  if (status === 'IN_PROGRESS') return '推进中'
  return '待闭环'
}

function closedLoopTag(status?: string) {
  if (status === 'COMPLETE') return 'success'
  if (status === 'IN_PROGRESS') return 'warning'
  return 'info'
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

async function loadData() {
  loading.value = true
  try {
    const [sheetResult, dashboardResult] = await Promise.all([
      listWorkoverOperationSheets(query),
      getWorkoverOperationDashboard()
    ])
    sheets.value = sheetResult.items
    total.value = sheetResult.total
    dashboard.value = dashboardResult
  } finally {
    loading.value = false
  }
}

async function loadPriority() {
  loading.value = true
  try {
    sheets.value = await listPriorityWorkoverOperationSheets()
    total.value = sheets.value.length
  } finally {
    loading.value = false
  }
}

function resetQuery() {
  query.page = 1
  query.status = ''
  query.project_id = undefined
  void loadData()
}

function openProgress(row: ManagedOperationSheet) {
  progressTarget.value = row
  progressValue.value = row.progress
  progressRemark.value = ''
  progressVisible.value = true
}

async function saveProgress() {
  if (!progressTarget.value) return
  saving.value = true
  try {
    await updateWorkoverOperationProgress(progressTarget.value.id, {
      progress: progressValue.value,
      progress_detail: { source: 'runtime_management', remark: progressRemark.value }
    })
    ElMessage.success('进度已更新')
    progressVisible.value = false
    await loadData()
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.closed-loop-cell {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.closed-loop-stages {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  width: 100%;
}
</style>
