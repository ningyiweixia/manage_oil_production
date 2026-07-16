<template>
  <section class="stats-bar operation-stats">
    <div class="stats-card">
      <span class="stats-label">总工单</span>
      <strong class="stats-value">{{ dashboard?.total_sheets || 0 }}</strong>
      <small>当前运行库</small>
    </div>
    <div class="stats-card">
      <span class="stats-label">待派工</span>
      <strong class="stats-value">{{ statusCounts.waiting }}</strong>
      <small>A5措施审核前</small>
    </div>
    <div class="stats-card">
      <span class="stats-label">待A5审核</span>
      <strong class="stats-value">{{ statusCounts.pendingA5 }}</strong>
      <small>队伍已锁定</small>
    </div>
    <div class="stats-card">
      <span class="stats-label">已下发</span>
      <strong class="stats-value">{{ statusCounts.dispatched }}</strong>
      <small>队伍已确认</small>
    </div>
    <div class="stats-card">
      <span class="stats-label">施工中</span>
      <strong class="stats-value">{{ statusCounts.working }}</strong>
      <small>现场执行中</small>
    </div>
    <div class="stats-card">
      <span class="stats-label">已完工</span>
      <strong class="stats-value">{{ statusCounts.finished }}</strong>
      <small>进度100%</small>
    </div>
    <div class="stats-card">
      <span class="stats-label">完工率</span>
      <strong class="stats-value">{{ dashboard?.completion_rate || 0 }}%</strong>
      <small>已完工 / 总工单</small>
    </div>
  </section>

  <section class="toolbar operation-filter">
    <el-form :model="query" inline>
      <el-form-item label="运行状态">
        <el-select v-model="query.status" clearable placeholder="全部状态" style="width: 150px">
          <el-option label="待派工" value="WAITING_DISPATCH" />
          <el-option label="待A5审核" value="PENDING_A5" />
          <el-option label="已下发" value="DISPATCHED" />
          <el-option label="施工中" value="WORKING" />
          <el-option label="已完工" value="FINISHED" />
        </el-select>
      </el-form-item>
      <el-form-item label="井号">
        <el-input v-model="query.well_no" clearable placeholder="输入井号" style="width: 140px" />
      </el-form-item>
      <el-form-item label="区块">
        <el-input v-model="query.block_name" clearable placeholder="输入区块" style="width: 140px" />
      </el-form-item>
      <el-form-item label="承包商/队伍">
        <el-input v-model="query.contractor_keyword" clearable placeholder="承包商或队伍" style="width: 170px" />
      </el-form-item>
      <el-form-item label="日期范围">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          style="width: 240px"
        />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="searchData">查询</el-button>
        <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>修井运行表</h2>
        <p>按井号、区块、队伍、状态和时间节点跟踪审批入库后的作业执行。</p>
      </div>
      <div class="panel-actions">
        <el-button v-if="canA5Sync" type="primary" :loading="syncingAll" :icon="Refresh" @click="syncAllA5">统一同步 A5</el-button>
        <el-button :icon="Refresh" @click="loadData">刷新</el-button>
      </div>
    </div>
    <div class="operation-table-scroll">
    <el-table v-loading="loading" :data="sheets" row-key="id" empty-text="暂无运行表" class="operation-table">
      <el-table-column label="作业编号" min-width="235">
        <template #default="{ row }">
          <div class="operation-no-cell">
            <el-tooltip :content="row.operation_no" placement="top">
              <span>{{ compactOperationNo(row.operation_no) }}</span>
            </el-tooltip>
            <el-button text circle :icon="DocumentCopy" title="复制作业编号" aria-label="复制作业编号" @click.stop="copyOperationNo(row.operation_no)" />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="井号" min-width="110" show-overflow-tooltip>
        <template #default="{ row }">
          <strong class="well-cell">{{ wellNo(row) }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="区块" min-width="90" show-overflow-tooltip>
        <template #default="{ row }">{{ row.project?.block_name || '-' }}</template>
      </el-table-column>
      <el-table-column label="承包商/队伍" min-width="190" show-overflow-tooltip>
        <template #default="{ row }">
          <div v-if="row.contractor" class="contractor-cell">
            <strong>{{ row.contractor.contractor_name }}</strong>
            <span>{{ row.contractor.team_name }}</span>
          </div>
          <span v-else class="muted-text">待分配</span>
        </template>
      </el-table-column>
      <el-table-column label="运行状态" min-width="105">
        <template #default="{ row }">
          <el-tag :type="sheetTag(row.status)" effect="plain">{{ sheetStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="施工进度" min-width="155">
        <template #default="{ row }">
          <el-progress :percentage="row.progress" :stroke-width="8" :status="progressStatus(row)" />
        </template>
      </el-table-column>
      <el-table-column label="时间节点" min-width="210">
        <template #default="{ row }">
          <div class="time-cell">
            <span>计划：{{ formatShortDate(row.planned_start_at) }} -> {{ formatShortDate(row.planned_end_at) }}</span>
            <span>实际：{{ formatShortDate(row.actual_start_at) }} -> {{ formatShortDate(row.actual_end_at) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="185">
        <template #default="{ row }">
          <div class="table-actions operation-actions">
            <el-button text type="primary" @click="openDetail(row)">查看详情</el-button>
            <el-button v-if="canDispatch && row.status === 'WAITING_DISPATCH'" text type="primary" :loading="loadingDispatchSheetId === row.id" @click="openDispatch(row)">分配队伍</el-button>
            <el-button v-if="canA5Sso && row.status === 'PENDING_A5'" text type="primary" :loading="openingA5SheetId === row.id" @click="openA5(row)">进入A5</el-button>
            <el-dropdown v-if="canA5Sync && row.status !== 'WAITING_DISPATCH' && row.status !== 'PENDING_A5'" trigger="click">
              <el-button text type="primary">更多<el-icon class="more-icon"><ArrowDown /></el-icon></el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item :disabled="syncingSheetId === row.id" @click="syncA5(row)">同步 A5 日报</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </el-table-column>
    </el-table>
    </div>
    <el-pagination
      v-model:current-page="query.page"
      v-model:page-size="query.page_size"
      class="pager"
      layout="total, sizes, prev, pager, next"
      :total="total"
      @change="loadData"
    />
  </section>

  <el-dialog v-model="dispatchVisible" title="分配队伍" width="560px">
    <el-form label-position="top">
      <el-form-item label="作业井">
        <el-input :model-value="dispatchTarget ? `${wellNo(dispatchTarget)} / ${dispatchTarget.operation_no}` : ''" disabled />
      </el-form-item>
      <el-form-item label="承包商队伍">
        <el-select v-model="dispatchContractorId" filterable placeholder="选择可用队伍" style="width: 100%">
          <el-option
            v-for="item in availableContractors"
            :key="item.id"
            :label="contractorOptionLabel(item)"
            :value="item.id"
            :disabled="Boolean(item.dispatchDisabledReason)"
          />
        </el-select>
        <div v-if="ineligibleContractorCount" class="dispatch-hint">
          {{ ineligibleContractorCount }} 支当日可用队伍因资质或施工能力不匹配，暂不可派工。
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dispatchVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveDispatch">确认分配</el-button>
    </template>
  </el-dialog>

  <el-drawer v-model="detailVisible" title="运行表详情" size="46%">
    <template v-if="detailTarget">
      <el-descriptions title="基础信息" :column="2" border>
        <el-descriptions-item label="作业编号">{{ detailTarget.operation_no }}</el-descriptions-item>
        <el-descriptions-item label="井号">{{ wellNo(detailTarget) }}</el-descriptions-item>
        <el-descriptions-item label="区块">{{ detailTarget.project?.block_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="措施类型">{{ measureTypeLabels(detailTarget).join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="项目来源">{{ projectSourceLabel(detailTarget.project?.data_source) }}</el-descriptions-item>
        <el-descriptions-item label="提报单位">{{ detailTarget.project?.report_unit || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-descriptions title="派工信息" :column="2" border class="detail-section">
        <el-descriptions-item label="承包商">{{ detailTarget.contractor?.contractor_name || '待分配' }}</el-descriptions-item>
        <el-descriptions-item label="队伍">{{ detailTarget.contractor?.team_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="队伍状态">{{ contractorStatusLabel(detailTarget.contractor?.status) }}</el-descriptions-item>
        <el-descriptions-item label="派工时间">{{ dispatchUpdatedAt(detailTarget) }}</el-descriptions-item>
      </el-descriptions>

      <el-descriptions title="进度与时间" :column="2" border class="detail-section">
        <el-descriptions-item label="当前状态">{{ sheetStatusLabel(detailTarget.status) }}</el-descriptions-item>
        <el-descriptions-item label="施工进度">{{ detailTarget.progress }}%</el-descriptions-item>
        <el-descriptions-item label="计划开始">{{ formatDateTime(detailTarget.planned_start_at) }}</el-descriptions-item>
        <el-descriptions-item label="计划结束">{{ formatDateTime(detailTarget.planned_end_at) }}</el-descriptions-item>
        <el-descriptions-item label="实际开始">{{ formatDateTime(detailTarget.actual_start_at) }}</el-descriptions-item>
        <el-descriptions-item label="实际结束">{{ formatDateTime(detailTarget.actual_end_at) }}</el-descriptions-item>
      </el-descriptions>

      <el-descriptions title="A5与闭环信息" :column="2" border class="detail-section">
        <el-descriptions-item label="A5审核状态">{{ detailTarget.a5_status || '未同步' }}</el-descriptions-item>
        <el-descriptions-item label="回写时间">{{ formatDateTime(detailTarget.last_a5_sync_at) }}</el-descriptions-item>
        <el-descriptions-item label="日报日期">{{ detailTarget.last_a5_report_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="同步结果">{{ detailTarget.a5_sync_result || '-' }}</el-descriptions-item>
        <el-descriptions-item v-if="detailTarget.a5_sync_error" label="同步失败" :span="2">{{ detailTarget.a5_sync_error }}</el-descriptions-item>
        <el-descriptions-item label="异常说明" :span="2">{{ detailTarget.a5_remark || '-' }}</el-descriptions-item>
        <el-descriptions-item label="物料状态">{{ materialStatusLabel(detailTarget.material_status?.status) }}</el-descriptions-item>
        <el-descriptions-item label="物料项数">{{ detailTarget.material_status?.total || 0 }}</el-descriptions-item>
        <el-descriptions-item label="完井记录">{{ detailTarget.completion_status?.status === 'RECORDED' ? '已登记' : '未登记' }}</el-descriptions-item>
        <el-descriptions-item label="闭环进度">
          {{ detailTarget.closed_loop_status?.done_count || 0 }}/{{ detailTarget.closed_loop_status?.total_count || 5 }}
        </el-descriptions-item>
      </el-descriptions>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, DocumentCopy, Refresh, Search } from '@element-plus/icons-vue'
import {
  createWorkoverA5Link,
  getWorkoverOperationDashboard,
  listWorkoverOperationSheets,
  syncAllWorkoverA5,
  syncWorkoverA5,
  type ManagedOperationSheet,
  type OperationDashboard
} from '../api/workoverOperation'
import {
  dispatchOperation,
  listContractors,
  type ContractorCapacity,
  type ContractorStatus,
  type OperationSheetQuery,
  type OperationStatus
} from '../api/contractor'
import { capabilityLabel, measureTypeLabel, projectSourceLabel } from '../utils/businessLabels'

const sheetStatusText: Record<OperationStatus, string> = {
  WAITING_DISPATCH: '待派工',
  PENDING_A5: '待A5审核',
  DISPATCHED: '已下发',
  WORKING: '施工中',
  FINISHED: '已完工',
  CANCELED: '已取消'
}
const contractorStatusText: Record<ContractorStatus, string> = { AVAILABLE: '可用', BUSY: '忙碌', OFFLINE: '离线', EXCEPTION: '异常' }
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
const syncingSheetId = ref<number>()
const syncingAll = ref(false)
const openingA5SheetId = ref<number>()
const loadingDispatchSheetId = ref<number>()
const sheets = ref<ManagedOperationSheet[]>([])
const total = ref(0)
const dashboard = ref<OperationDashboard | null>(null)
const dateRange = ref<[string, string] | []>([])
const dispatchVisible = ref(false)
const dispatchTarget = ref<ManagedOperationSheet | null>(null)
const dispatchContractorId = ref<number>()
type DispatchContractor = ContractorCapacity & { dispatchDisabledReason?: string }
const availableContractors = ref<DispatchContractor[]>([])
const ineligibleContractorCount = computed(() => availableContractors.value.filter((item) => item.dispatchDisabledReason).length)
const detailVisible = ref(false)
const detailTarget = ref<ManagedOperationSheet | null>(null)
let dataRequestId = 0
let dispatchRequestId = 0
const query = reactive<OperationSheetQuery>({ page: 1, page_size: 10, status: '' })
const permissions = (() => {
  try { return new Set<string>(JSON.parse(localStorage.getItem('permissions') || '[]')) } catch { return new Set<string>() }
})()
const canDispatch = computed(() => permissions.has('workover_operation:dispatch') || permissions.has('operation-sheet:dispatch'))
const canA5Sso = computed(() => permissions.has('a5:sso'))
const canA5Sync = computed(() => permissions.has('workover_operation:a5_sync'))
const capabilityAlias: Record<string, string> = {
  major_workover: 'major_repair', pump_repair: 'major_repair', pump_inspection: 'major_repair',
  sand_washing: 'sand_control', tubing_replacement: 'major_repair', casing_damage_treatment: 'major_repair'
}

const statusCounts = computed(() => ({
  waiting: dashboard.value?.status_distribution.waiting_dispatch || 0,
  pendingA5: dashboard.value?.status_distribution.pending_a5 || 0,
  dispatched: dashboard.value?.status_distribution.dispatched || 0,
  working: dashboard.value?.status_distribution.working || 0,
  finished: dashboard.value?.status_distribution.finished || 0
}))

function sheetStatusLabel(status: OperationStatus) {
  return sheetStatusText[status] || status
}

function sheetTag(status: OperationStatus) {
  if (status === 'FINISHED') return 'success'
  if (status === 'CANCELED') return 'danger'
  if (status === 'WAITING_DISPATCH') return 'warning'
  if (status === 'PENDING_A5') return 'warning'
  if (status === 'WORKING') return 'primary'
  return 'info'
}

function contractorStatusLabel(status?: ContractorStatus | string) {
  return status ? contractorStatusText[status as ContractorStatus] || status : '-'
}

function materialStatusLabel(status?: string) {
  return materialStatusText[status || 'NONE'] || status || '无需求'
}

function progressStatus(row: ManagedOperationSheet) {
  if (row.status === 'FINISHED' || row.progress >= 100) return 'success'
  return undefined
}

function wellNo(row: ManagedOperationSheet) {
  return row.project?.well_no || row.project_well_no || '-'
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 19)
}

function formatShortDate(value?: string | null) {
  if (!value) return '-'
  const normalized = value.slice(0, 10)
  return normalized.length === 10 ? normalized.slice(5) : normalized
}

function compactOperationNo(value: string) {
  if (value.length <= 24) return value
  return `${value.slice(0, 16)}…${value.slice(-5)}`
}

async function copyOperationNo(value: string) {
  try {
    await navigator.clipboard.writeText(value)
    ElMessage.success('作业编号已复制')
  } catch {
    ElMessage.error('复制失败，请使用悬浮提示查看完整编号')
  }
}

function measureTypes(row: ManagedOperationSheet) {
  const measures = row.project?.measures_jsonb?.measures
  if (!Array.isArray(measures)) return []
  return measures.map((item) => item.measure_type).filter(Boolean)
}

function measureTypeLabels(row: ManagedOperationSheet) {
  return measureTypes(row).map(measureTypeLabel)
}

function dispatchUpdatedAt(row: ManagedOperationSheet) {
  const detail = row.progress_detail?.dispatch
  if (detail && typeof detail === 'object' && 'updated_at' in detail) {
    return formatDateTime(String(detail.updated_at))
  }
  return '-'
}

function applyDateRange() {
  query.start_date = dateRange.value[0]
  query.end_date = dateRange.value[1]
}

function showRequestError(error: unknown, fallback: string) {
  if ((error as { response?: { status?: number } })?.response?.status === 401) return
  ElMessage.error(error instanceof Error && error.message ? error.message : fallback)
}

async function loadData() {
  const requestId = ++dataRequestId
  loading.value = true
  applyDateRange()
  const requestQuery = { ...query }
  try {
    const [sheetResult, dashboardResult] = await Promise.all([
      listWorkoverOperationSheets(requestQuery),
      getWorkoverOperationDashboard()
    ])
    if (requestId !== dataRequestId) return
    sheets.value = sheetResult.items
    total.value = sheetResult.total
    dashboard.value = dashboardResult
    if (detailTarget.value) {
      const refreshed = sheetResult.items.find((item) => item.id === detailTarget.value?.id)
      if (refreshed) detailTarget.value = refreshed
      else {
        detailTarget.value = null
        detailVisible.value = false
      }
    }
  } catch (error) {
    if (requestId !== dataRequestId) return
    showRequestError(error, '修井运行数据加载失败')
  } finally {
    if (requestId === dataRequestId) loading.value = false
  }
}

async function searchData() {
  query.page = 1
  await loadData()
}

function resetQuery() {
  query.page = 1
  query.status = ''
  query.project_id = undefined
  query.contractor_capacity_id = undefined
  query.well_no = undefined
  query.block_name = undefined
  query.contractor_keyword = undefined
  query.start_date = undefined
  query.end_date = undefined
  dateRange.value = []
  void loadData()
}

async function openDispatch(row: ManagedOperationSheet) {
  const requestId = ++dispatchRequestId
  loadingDispatchSheetId.value = row.id
  dispatchTarget.value = row
  dispatchContractorId.value = undefined
  dispatchVisible.value = true
  const today = formatLocalDate(new Date())
  const requiredCapabilities = measureTypes(row)
  try {
    const result = await listContractors({
      page: 1,
      page_size: 100,
      status: 'AVAILABLE',
      sync_status: 'SYNCED',
      report_date: today
    })
    if (requestId !== dispatchRequestId || dispatchTarget.value?.id !== row.id) return
    availableContractors.value = result.items.map((item) => {
      const reasons: string[] = []
      if (item.available_count <= 0) reasons.push('可用队伍数不足')
      if (!item.qualification_expire_at) reasons.push('未维护施工资质有效期')
      else if (item.qualification_expire_at < today) reasons.push('施工资质已过期')
      const missingCapabilities = requiredCapabilities.filter((capability) => !isCapabilityEnabled(item.capability_tags?.[capabilityAlias[capability] || capability]))
      if (missingCapabilities.length) reasons.push(`缺少施工能力：${missingCapabilities.map((capability) => capabilityLabel(capabilityAlias[capability] || capability)).join('、')}`)
      return { ...item, dispatchDisabledReason: reasons.join('；') || undefined }
    })
  } catch (error) {
    if (requestId !== dispatchRequestId) return
    dispatchVisible.value = false
    showRequestError(error, '可用队伍加载失败')
  } finally {
    if (requestId === dispatchRequestId) loadingDispatchSheetId.value = undefined
  }
}

function isCapabilityEnabled(value: unknown) {
  return value === true || value === 'true' || value === 1
}

function contractorOptionLabel(item: DispatchContractor) {
  const base = `${item.contractor_name} / ${item.team_name}（可用 ${item.available_count}）`
  return item.dispatchDisabledReason ? `${base} — 不可派工：${item.dispatchDisabledReason}` : base
}

function formatLocalDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

async function saveDispatch() {
  if (!dispatchTarget.value || !dispatchContractorId.value) {
    ElMessage.warning('请选择承包商队伍')
    return
  }
  const a5Window = window.open('', '_blank')
  saving.value = true
  try {
    const result = await dispatchOperation({
      operation_sheet_id: dispatchTarget.value.id,
      contractor_capacity_id: dispatchContractorId.value,
      redirect_path: '/measure-review'
    })
    ElMessage.success('已分配队伍，请在 A5 完成措施审核及下发')
    dispatchVisible.value = false
    if (result.redirect_url && a5Window) a5Window.location.href = result.redirect_url
    else if (result.redirect_url) ElMessage.warning('浏览器拦截了A5窗口，请点击“进入A5”重试')
    await loadData()
  } catch (error) {
    a5Window?.close()
    showRequestError(error, '派工失败')
  } finally {
    saving.value = false
  }
}

async function openA5(row: ManagedOperationSheet) {
  if (openingA5SheetId.value === row.id) return
  const a5Window = window.open('', '_blank')
  openingA5SheetId.value = row.id
  try {
    const result = await createWorkoverA5Link(row.id)
    if (a5Window) a5Window.location.href = result.redirect_url
    else ElMessage.warning('浏览器拦截了A5窗口，请允许本站弹出窗口')
  } catch (error) {
    a5Window?.close()
    showRequestError(error, 'A5页面打开失败')
  } finally {
    openingA5SheetId.value = undefined
  }
}

async function syncA5(row: ManagedOperationSheet) {
  syncingSheetId.value = row.id
  try {
    const result = await syncWorkoverA5(row.id)
    if (result.failed_count > 0) ElMessage.warning(result.message)
    else ElMessage.success(result.message)
    await loadData()
  } catch (error) {
    showRequestError(error, 'A5日报同步失败')
  } finally {
    syncingSheetId.value = undefined
  }
}

async function syncAllA5() {
  syncingAll.value = true
  try {
    const result = await syncAllWorkoverA5()
    if (result.failed_count > 0) ElMessage.warning(result.message)
    else ElMessage.success(result.message)
    await loadData()
  } catch (error) {
    showRequestError(error, 'A5统一同步失败')
  } finally {
    syncingAll.value = false
  }
}

function openDetail(row: ManagedOperationSheet) {
  detailTarget.value = row
  detailVisible.value = true
}

onMounted(loadData)
</script>

<style scoped>
.operation-stats {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.operation-filter :deep(.el-form) {
  display: flex;
  flex-wrap: wrap;
  gap: 0 4px;
}

.operation-stats .stats-card small {
  display: block;
  margin-top: 6px;
  color: #667085;
  font-size: 12px;
}

.well-cell {
  color: #172033;
}

.contractor-cell,
.time-cell {
  display: grid;
  gap: 2px;
  line-height: 1.35;
}

.contractor-cell strong {
  overflow: hidden;
  color: #172033;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.contractor-cell span,
.time-cell span {
  color: #667085;
  font-size: 12px;
}

.operation-actions {
  gap: 8px;
  white-space: nowrap;
}

.panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.more-icon {
  margin-left: 3px;
  vertical-align: -1px;
}

.operation-table-scroll {
  overflow-x: auto;
}

.operation-table {
  min-width: 1280px;
}

.operation-no-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.operation-no-cell > span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dispatch-hint {
  margin-top: 8px;
  color: #8a5a00;
  font-size: 12px;
  line-height: 1.5;
}

.detail-section {
  margin-top: 18px;
}

@media (max-width: 1180px) {
  .operation-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

}

@media (max-width: 720px) {
  .operation-stats {
    grid-template-columns: 1fr;
  }
}
</style>
