<template>
  <section v-if="canViewGlobalSync" class="sync-strip">
    <div class="sync-main">
      <div class="sync-state">
        <span class="state-dot" :class="connectionClass" />
        <div>
          <strong>承包商系统对接</strong>
          <p>{{ syncSummary.connection_status }} · 最近同步 {{ formatTime(syncSummary.last_sync_time) }}</p>
        </div>
      </div>
      <div class="sync-stats">
        <span>新增 {{ syncSummary.created_count }}</span>
        <span>更新 {{ syncSummary.updated_count }}</span>
        <span>忽略 {{ syncSummary.ignored_count }}</span>
        <span>异常 {{ syncSummary.exception_count || syncSummary.failed_count }}</span>
      </div>
    </div>
    <div class="sync-actions">
      <el-tag :type="syncResultTag(syncSummary.last_sync_status)" effect="plain">
        {{ syncResultLabel(syncSummary.last_sync_status) }}
      </el-tag>
      <el-button v-if="canSyncContractors" type="primary" :icon="Refresh" :loading="syncing" :disabled="syncDisabled" @click="runSync">立即同步</el-button>
      <el-button :icon="Document" @click="openLogs">查看同步日志</el-button>
      <el-button :icon="Setting" @click="ElMessage.info('接口配置由环境变量统一管理')">接口配置</el-button>
    </div>
  </section>

  <section class="toolbar">
    <el-form :model="contractorQuery" inline>
      <el-form-item label="报备日期">
        <el-date-picker v-model="contractorQuery.report_date" value-format="YYYY-MM-DD" clearable />
      </el-form-item>
      <el-form-item label="承包商">
        <el-input v-model="contractorQuery.contractor_name" clearable placeholder="承包商名称" />
      </el-form-item>
      <el-form-item label="队伍">
        <el-input v-model="contractorQuery.team_name" clearable placeholder="队伍名称" />
      </el-form-item>
      <el-form-item label="队伍状态">
        <el-select v-model="contractorQuery.status" clearable placeholder="全部" style="width: 132px">
          <el-option label="可用" value="AVAILABLE" />
          <el-option label="忙碌" value="BUSY" />
          <el-option label="离线" value="OFFLINE" />
          <el-option label="异常" value="EXCEPTION" />
        </el-select>
      </el-form-item>
      <el-form-item label="施工能力">
        <el-select v-model="contractorQuery.capability_tag" clearable placeholder="全部" style="width: 140px">
          <el-option v-for="item in capabilityOptions" :key="item.key" :label="item.label" :value="item.key" />
        </el-select>
      </el-form-item>
      <el-form-item label="数据来源">
        <el-select v-model="contractorQuery.source_type" clearable placeholder="全部" style="width: 140px">
          <el-option label="外部同步" value="EXTERNAL_SYNC" />
          <el-option label="本地补录" value="LOCAL_SUPPLEMENT" />
          <el-option label="同步异常" value="SYNC_ERROR" />
        </el-select>
      </el-form-item>
      <el-form-item label="同步状态">
        <el-select v-model="contractorQuery.sync_status" clearable placeholder="全部" style="width: 140px">
          <el-option label="已同步" value="SYNCED" />
          <el-option label="待确认" value="PENDING_CONFIRM" />
          <el-option label="冲突" value="CONFLICT" />
          <el-option label="失效" value="INVALID" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="searchContractors">查询</el-button>
        <el-button v-if="canCreateContractor" :icon="EditPen" @click="openSupplement">异常补录</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="metric-grid">
    <div v-for="item in metrics" :key="item.label" class="metric-card">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <h2>运力快照</h2>
      <span>外部承包商系统为权威来源，本系统保留同步确认、异常处理和派工引用。</span>
    </div>
    <el-table
      v-loading="loading"
      class="capacity-snapshot-table"
      :data="contractors"
      row-key="id"
      table-layout="auto"
      empty-text="暂无运力快照"
    >
      <el-table-column label="承包商 / 队伍" min-width="220">
        <template #default="{ row }">
          <div class="team-cell">
            <strong>{{ row.contractor_name }}</strong>
            <span>{{ row.team_name }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="report_date" label="报备日期" min-width="112" />
      <el-table-column prop="available_count" label="可用数" min-width="78" />
      <el-table-column label="队伍状态" min-width="96">
        <template #default="{ row }">
          <el-tag :type="contractorTag(row.status)">{{ contractorStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="施工能力" min-width="180">
        <template #default="{ row }">
          <div class="capability-tags">
            <el-tag v-for="tag in readableCapabilities(row.capability_tags)" :key="tag" class="tag-gap" effect="plain">
              {{ tag }}
            </el-tag>
            <span v-if="readableCapabilities(row.capability_tags).length === 0" class="muted">未标注</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="来源" min-width="108">
        <template #default="{ row }">
          <el-tag effect="plain">{{ sourceLabel(row.source_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="同步状态" min-width="116">
        <template #default="{ row }">
          <el-tag :type="syncStatusTag(normalizeSyncStatus(row.sync_status))">
            {{ syncStatusLabel(normalizeSyncStatus(row.sync_status)) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="占用" min-width="72" align="center">
        <template #default="{ row }">{{ row.occupied_count ?? 0 }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="204">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button link type="primary" :icon="View" @click="openDetail(row)">详情</el-button>
            <el-button v-if="canUpdateContractor" link type="success" :icon="Check" :loading="actingContractorId === row.id" :disabled="normalizeSyncStatus(row.sync_status) !== 'PENDING_CONFIRM' || ['OFFLINE', 'EXCEPTION'].includes(row.status)" @click="confirmRow(row)">确认</el-button>
            <el-button link :icon="Link" @click="openDetail(row, 'occupy')">工单</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    <div class="pager">
      <el-pagination
        v-model:current-page="contractorQuery.page"
        v-model:page-size="contractorQuery.page_size"
        :total="total"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50, 100]"
        @current-change="loadContractors"
        @size-change="loadContractors"
      />
    </div>
  </section>

  <el-drawer v-model="detailVisible" title="运力详情" size="58%">
    <template v-if="current">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="基础信息" name="base">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="承包商">{{ current.contractor_name }}</el-descriptions-item>
            <el-descriptions-item label="队伍">{{ current.team_name }}</el-descriptions-item>
            <el-descriptions-item label="联系人">{{ current.contact_name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="联系电话">{{ current.contact_phone || '-' }}</el-descriptions-item>
            <el-descriptions-item label="报备日期">{{ current.report_date }}</el-descriptions-item>
            <el-descriptions-item label="外部ID">{{ current.external_system_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="外部状态">{{ externalStatusLabel(current.external_status, current.source_type) }}</el-descriptions-item>
            <el-descriptions-item label="数据来源">{{ sourceLabel(current.source_type) }}</el-descriptions-item>
            <el-descriptions-item label="最近同步">{{ formatTime(current.last_synced_at) }}</el-descriptions-item>
            <el-descriptions-item label="确认时间">{{ formatTime(current.confirmed_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="能力信息" name="capacity">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="能力标签">
              <el-tag v-for="tag in readableCapabilities(current.capability_tags)" :key="tag" class="tag-gap" effect="plain">{{ tag }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="资质有效期">{{ current.qualification_expire_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="设备信息">{{ current.equipment_summary || '-' }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="占用情况" name="occupy">
          <el-table :data="operationLinks" empty-text="暂无关联运行表">
            <el-table-column prop="operation_no" label="运行表号" min-width="140" />
            <el-table-column prop="well_no" label="井号" width="120" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">{{ operationStatusLabel(row.status) }}</template>
            </el-table-column>
            <el-table-column prop="a5_status" label="A5状态" min-width="140" />
            <el-table-column label="派工时间" width="170">
              <template #default="{ row }">{{ formatTime(row.dispatch_time) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
          <el-tab-pane v-if="canViewGlobalSync" label="同步日志" name="logs">
          <el-table :data="currentLogs" empty-text="暂无当前队伍同步日志">
            <el-table-column label="同步时间" min-width="170">
              <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
            </el-table-column>
            <el-table-column label="方式" width="120">
              <template #default="{ row }">{{ syncTypeLabel(row.sync_type) }}</template>
            </el-table-column>
            <el-table-column label="结果" width="100">
              <template #default="{ row }"><el-tag :type="syncResultTag(row.status)">{{ syncResultLabel(row.status) }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="success_count" label="成功" width="76" />
            <el-table-column prop="failed_count" label="失败" width="76" />
            <el-table-column prop="error_message" label="失败原因" min-width="160" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane v-if="canUpdateContractor" label="异常处理" name="exception">
          <el-alert v-if="current.sync_error_message" type="warning" :closable="false" :title="current.sync_error_message" />
          <div class="exception-actions">
            <el-input v-model="exceptionReason" type="textarea" :rows="4" placeholder="填写异常原因" />
            <div class="exception-buttons">
              <el-button type="warning" :loading="savingException" @click="submitException">标记异常</el-button>
              <el-button :loading="savingException" @click="resolveException">解除异常</el-button>
              <el-button type="success" :loading="savingException || actingContractorId === current.id" @click="confirmRow(current)">人工确认</el-button>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </el-drawer>

  <el-dialog v-model="logVisible" title="同步日志" width="860px">
    <el-table v-loading="logLoading" :data="logs" max-height="420" empty-text="暂无同步日志">
      <el-table-column label="同步时间" min-width="170">
        <template #default="{ row }">{{ formatTime(row.started_at) }}</template>
      </el-table-column>
      <el-table-column label="方式" width="120">
        <template #default="{ row }">{{ syncTypeLabel(row.sync_type) }}</template>
      </el-table-column>
      <el-table-column label="结果" width="100">
        <template #default="{ row }"><el-tag :type="syncResultTag(row.status)">{{ syncResultLabel(row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="success_count" label="成功" width="76" />
      <el-table-column prop="failed_count" label="失败" width="76" />
      <el-table-column prop="created_count" label="新增" width="76" />
      <el-table-column prop="updated_count" label="更新" width="76" />
      <el-table-column prop="ignored_count" label="忽略" width="76" />
      <el-table-column prop="error_message" label="失败原因" min-width="180" />
    </el-table>
  </el-dialog>

  <el-dialog v-model="supplementVisible" title="异常补录" width="620px" @closed="resetSupplementForm">
    <el-form :model="contractorForm" label-width="108px">
      <el-form-item label="承包商"><el-input v-model="contractorForm.contractor_name" /></el-form-item>
      <el-form-item label="队伍名称"><el-input v-model="contractorForm.team_name" /></el-form-item>
      <el-form-item label="报备日期"><el-date-picker v-model="contractorForm.report_date" value-format="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="可用数量"><el-input-number v-model="contractorForm.available_count" :min="0" /></el-form-item>
      <el-form-item label="状态">
        <el-select v-model="contractorForm.status">
          <el-option label="可用" value="AVAILABLE" />
          <el-option label="忙碌" value="BUSY" />
          <el-option label="离线" value="OFFLINE" />
          <el-option label="异常" value="EXCEPTION" />
        </el-select>
      </el-form-item>
      <el-form-item label="施工能力">
        <div class="capability-switches">
          <el-checkbox v-for="item in capabilityOptions" :key="item.key" v-model="capabilityForm[item.key]">
            {{ item.label }}
          </el-checkbox>
        </div>
      </el-form-item>
      <el-form-item label="补录原因"><el-input v-model="contractorForm.sync_error_message" type="textarea" :rows="3" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="supplementVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveSupplement">保存补录</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Document, EditPen, Link, Refresh, Search, Setting, View } from '@element-plus/icons-vue'
import {
  confirmContractor,
  createContractor,
  getContractorOverview,
  getContractorSyncSummary,
  listContractorOperationSheets,
  listContractorSyncLogs,
  listContractors,
  markContractorException,
  resolveContractorException,
  syncContractors,
  type ContractorCapacity,
  type ContractorOperationLink,
  type ContractorOverview,
  type ContractorQuery,
  type ContractorStatus,
  type ContractorSyncLog,
  type ContractorSyncResultStatus,
  type ContractorSyncStatus
} from '../api/contractor'

function localDateString(value = new Date()) {
  const year = value.getFullYear()
  const month = `${value.getMonth() + 1}`.padStart(2, '0')
  const day = `${value.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const today = localDateString()
const contractorStatusText: Record<ContractorStatus, string> = { AVAILABLE: '可用', BUSY: '忙碌', OFFLINE: '离线', EXCEPTION: '异常' }
const syncStatusText: Record<ContractorSyncStatus, string> = { SYNCED: '已同步', PENDING_CONFIRM: '待确认', CONFLICT: '冲突', INVALID: '失效' }
const capabilityText: Record<string, string> = {
  major_repair: '大修资质',
  acidizing: '酸化',
  fracturing: '压裂',
  sand_control: '防砂',
  deep_well: '深井',
  demo: '通用作业'
}

const loading = ref(false)
const syncing = ref(false)
const saving = ref(false)
const savingException = ref(false)
const actingContractorId = ref<number>()
const logLoading = ref(false)
const contractors = ref<ContractorCapacity[]>([])
const logs = ref<ContractorSyncLog[]>([])
const operationLinks = ref<ContractorOperationLink[]>([])
const total = ref(0)
const detailVisible = ref(false)
const logVisible = ref(false)
const supplementVisible = ref(false)
const activeTab = ref('base')
const current = ref<ContractorCapacity | null>(null)
let contractorRequestId = 0
const exceptionReason = ref('')
const capabilityOptions = [
  { key: 'demo', label: '通用作业' },
  { key: 'major_repair', label: '大修资质' },
  { key: 'acidizing', label: '酸化' },
  { key: 'fracturing', label: '压裂' },
  { key: 'sand_control', label: '防砂' },
  { key: 'deep_well', label: '深井' }
]
const capabilityForm = reactive<Record<string, boolean>>(Object.fromEntries(capabilityOptions.map((item) => [item.key, false])))
const syncSummary = reactive({ connection_status: '未配置', created_count: 0, updated_count: 0, ignored_count: 0, failed_count: 0, exception_count: 0, last_sync_time: null, last_sync_status: null } as Awaited<ReturnType<typeof getContractorSyncSummary>>)
const overview = reactive<ContractorOverview>({
  reported_team_count: 0,
  available_team_count: 0,
  busy_team_count: 0,
  offline_team_count: 0,
  sync_exception_count: 0,
  major_repair_team_count: 0
})
const contractorQuery = reactive<ContractorQuery>({ page: 1, page_size: 20, report_date: today, status: '', source_type: '', sync_status: '' })
const permissions = (() => {
  try { return new Set<string>(JSON.parse(localStorage.getItem('permissions') || '[]')) } catch { return new Set<string>() }
})()
const canCreateContractor = computed(() => permissions.has('contractor:create'))
const canUpdateContractor = computed(() => permissions.has('contractor:update'))
const contractorForm = reactive({
  contractor_name: '',
  team_name: '',
  report_date: today,
  available_count: 1,
  status: 'AVAILABLE' as ContractorStatus,
  capability_tags: {},
  sync_error_message: ''
})

const displayedOverview = computed(() => {
  const apiHasData = Object.values(overview).some((value) => value > 0)
  if (apiHasData || contractors.value.length === 0) {
    return overview
  }
    return {
      reported_team_count: total.value || contractors.value.length,
    available_team_count: contractors.value.filter((item) => item.status === 'AVAILABLE').length,
    busy_team_count: contractors.value.filter((item) => item.status === 'BUSY').length,
    offline_team_count: contractors.value.filter((item) => item.status === 'OFFLINE').length,
    sync_exception_count: contractors.value.filter((item) => item.sync_status === 'CONFLICT' || item.sync_status === 'INVALID').length,
    major_repair_team_count: contractors.value.filter((item) => Boolean((item.capability_tags || {}).major_repair)).length
  }
})
const reportedMetricLabel = computed(() => contractorQuery.report_date ? `${contractorQuery.report_date} 报备队伍数` : '报备队伍数')
const metrics = computed(() => [
  { label: reportedMetricLabel.value, value: displayedOverview.value.reported_team_count },
  { label: '当前可用队伍数', value: displayedOverview.value.available_team_count },
  { label: '忙碌队伍数', value: displayedOverview.value.busy_team_count },
  { label: '离线队伍数', value: displayedOverview.value.offline_team_count },
  { label: '同步异常数', value: displayedOverview.value.sync_exception_count },
  { label: '大修资质队伍数', value: displayedOverview.value.major_repair_team_count }
])
const connectionClass = computed(() => syncSummary.connection_status === '正常' ? 'ok' : syncSummary.connection_status === '演示模式' || syncSummary.connection_status === '未配置' ? 'unset' : 'bad')
const syncDisabled = computed(() => syncSummary.connection_status === '异常')
const canViewGlobalSync = computed(() => {
  try {
    const user = JSON.parse(localStorage.getItem('current_user') || '{}')
    const roles = (user.roles || []).map((role: { code?: string }) => role.code)
    return Boolean(user.is_superuser || roles.some((code: string) => ['super_admin', 'ops_admin', 'business_reviewer', 'process_reviewer', 'project_pool_admin'].includes(code)))
  } catch {
    return false
  }
})
const canSyncContractors = computed(() => canViewGlobalSync.value && canUpdateContractor.value)

function showRequestError(error: unknown, fallback: string) {
  if ((error as { response?: { status?: number } })?.response?.status === 401) return
  ElMessage.error(error instanceof Error && error.message ? error.message : fallback)
}
const currentLogs = computed(() => {
  if (!current.value) {
    return []
  }
  return logs.value.filter((row) => {
    const summary = row.raw_summary || {}
    if (current.value?.external_system_id && summary.external_system_id === current.value.external_system_id) {
      return true
    }
    return !summary.external_system_id && summary.report_date === current.value?.report_date
  })
})

function formatTime(value?: string | null) {
  return value ? value.replace('T', ' ').slice(0, 19) : '-'
}

function contractorTag(status: ContractorStatus) {
  return status === 'AVAILABLE' ? 'success' : status === 'BUSY' ? 'warning' : status === 'EXCEPTION' ? 'danger' : 'info'
}

function contractorStatusLabel(status: ContractorStatus) {
  return contractorStatusText[status] || status
}

function normalizeSyncStatus(status?: ContractorSyncStatus | '' | null): ContractorSyncStatus {
  return status && syncStatusText[status] ? status : 'PENDING_CONFIRM'
}

function syncStatusLabel(status: ContractorSyncStatus) {
  return syncStatusText[status] || status
}

function syncStatusTag(status: ContractorSyncStatus) {
  return status === 'SYNCED' ? 'success' : status === 'PENDING_CONFIRM' ? 'warning' : 'danger'
}

function syncResultLabel(status?: ContractorSyncResultStatus | null) {
  return status === 'SUCCESS' ? '成功' : status === 'FAILED' ? '失败' : status === 'PARTIAL' ? '部分失败' : '未同步'
}

function syncResultTag(status?: ContractorSyncResultStatus | null) {
  return status === 'SUCCESS' ? 'success' : status === 'FAILED' ? 'danger' : status === 'PARTIAL' ? 'warning' : 'info'
}

function syncTypeLabel(value: string) {
  return value === 'SCHEDULED' ? '定时' : value === 'SINGLE_TEAM' ? '单队伍重试' : '手动'
}

function sourceLabel(value: string) {
  return value === 'EXTERNAL_SYNC' ? '外部同步' : value === 'SYNC_ERROR' ? '同步异常' : '本地补录'
}

function externalStatusLabel(value?: string | null, sourceType?: string) {
  if (value) {
    return value === 'AVAILABLE' ? '可用' : value === 'BUSY' ? '忙碌' : value === 'OFFLINE' ? '离线' : value === 'EXCEPTION' ? '异常' : value
  }
  return sourceType === 'LOCAL_SUPPLEMENT' ? '本地补录' : '-'
}

function operationStatusLabel(value: string) {
  const map: Record<string, string> = { WAITING_DISPATCH: '待派工', PENDING_A5: '待A5审核', DISPATCHED: '已下发', WORKING: '施工中', FINISHED: '已完工', CANCELED: '已取消' }
  return map[value] || value
}

function readableCapabilities(tags: Record<string, unknown>) {
  return Object.entries(tags || {})
    .filter(([, value]) => value === true || value === 'true' || value === 1)
    .map(([key]) => capabilityText[key] || key)
}

async function loadSummary() {
  try {
    Object.assign(syncSummary, await getContractorSyncSummary())
  } catch (error) {
    showRequestError(error, '同步摘要加载失败')
  }
}

async function loadOverview(reportDate?: string) {
  return getContractorOverview(reportDate)
}

async function loadContractors() {
  const requestId = ++contractorRequestId
  const requestQuery = { ...contractorQuery }
  loading.value = true
  try {
    const [result, overviewResult] = await Promise.all([
      listContractors(requestQuery),
      loadOverview(requestQuery.report_date)
    ])
    if (requestId !== contractorRequestId) return
    contractors.value = result.items
    total.value = result.total
    Object.assign(overview, overviewResult)
    if (current.value) {
      const refreshed = result.items.find((item) => item.id === current.value?.id)
      if (refreshed) current.value = refreshed
      else {
        current.value = null
        detailVisible.value = false
      }
    }
  } catch (error) {
    if (requestId !== contractorRequestId) return
    showRequestError(error, '运力快照加载失败')
  } finally {
    if (requestId === contractorRequestId) loading.value = false
  }
}

async function loadLogs() {
  logLoading.value = true
  try {
    const result = await listContractorSyncLogs({ page: 1, page_size: 20 })
    logs.value = result.items
  } catch (error) {
    showRequestError(error, '同步日志加载失败')
  } finally {
    logLoading.value = false
  }
}

async function searchContractors() {
  contractorQuery.page = 1
  await loadContractors()
}

async function runSync() {
  if (syncDisabled.value) {
    ElMessage.warning('承包商接口异常，暂不能同步')
    return
  }
  syncing.value = true
  try {
    const result = await syncContractors({ report_date: contractorQuery.report_date || today })
    if (result.status === 'FAILED') {
      ElMessage.error(result.error_message || '同步失败')
    } else if (result.status === 'PARTIAL') {
      ElMessage.warning(`同步部分完成：成功 ${result.success_count}，失败 ${result.failed_count}`)
    } else {
      ElMessage.success('承包商运力同步完成')
    }
    await Promise.all([loadSummary(), loadContractors(), loadLogs()])
  } catch (error) {
    showRequestError(error, '承包商运力同步失败')
  } finally {
    syncing.value = false
  }
}

async function openLogs() {
  logVisible.value = true
  await loadLogs()
}

async function openDetail(row: ContractorCapacity, tab = 'base') {
  current.value = row
  activeTab.value = tab
  detailVisible.value = true
  exceptionReason.value = row.sync_error_message || ''
  if (tab === 'occupy') {
    try {
      operationLinks.value = await listContractorOperationSheets(row.id)
    } catch (error) {
      showRequestError(error, '关联工单加载失败')
    }
  }
}

async function handleTabChange(name: string | number) {
  if (!current.value) return
  if (name === 'occupy') {
    try {
      operationLinks.value = await listContractorOperationSheets(current.value.id)
    } catch (error) {
      showRequestError(error, '关联工单加载失败')
    }
  }
  if (name === 'logs') {
    await loadLogs()
  }
}

async function confirmRow(row: ContractorCapacity) {
  if (actingContractorId.value === row.id) return
  actingContractorId.value = row.id
  try {
    const updated = await confirmContractor(row.id)
    if (current.value?.id === row.id) current.value = updated
    ElMessage.success('已确认同步')
    await Promise.all(canViewGlobalSync.value ? [loadSummary(), loadContractors()] : [loadContractors()])
  } catch (error) {
    showRequestError(error, '运力确认失败')
  } finally {
    actingContractorId.value = undefined
  }
}

async function submitException() {
  if (!current.value) return
  if (!exceptionReason.value.trim()) {
    ElMessage.warning('请填写异常原因')
    return
  }
  savingException.value = true
  try {
    const updated = await markContractorException(current.value.id, exceptionReason.value.trim())
    current.value = updated
    ElMessage.success('已标记异常')
    await Promise.all(canViewGlobalSync.value ? [loadSummary(), loadContractors()] : [loadContractors()])
  } catch (error) {
    showRequestError(error, '异常标记失败')
  } finally {
    savingException.value = false
  }
}

async function resolveException() {
  if (!current.value) return
  savingException.value = true
  try {
    const updated = await resolveContractorException(current.value.id)
    current.value = updated
    ElMessage.success('异常已解除')
    await Promise.all(canViewGlobalSync.value ? [loadSummary(), loadContractors()] : [loadContractors()])
  } catch (error) {
    showRequestError(error, '异常解除失败')
  } finally {
    savingException.value = false
  }
}

function openSupplement() {
  ElMessageBox.confirm('本地补录仅用于外部接口异常时的应急处理。', '异常补录', { type: 'warning' })
    .then(() => {
      resetSupplementForm()
      supplementVisible.value = true
    })
    .catch(() => undefined)
}

function resetSupplementForm() {
  Object.assign(contractorForm, {
    contractor_name: '',
    team_name: '',
    report_date: contractorQuery.report_date || today,
    available_count: 1,
    status: 'AVAILABLE',
    capability_tags: {},
    sync_error_message: ''
  })
  Object.assign(capabilityForm, Object.fromEntries(capabilityOptions.map((item) => [item.key, false])))
}

async function saveSupplement() {
  if (!contractorForm.contractor_name.trim() || !contractorForm.team_name.trim() || !contractorForm.report_date) {
    ElMessage.warning('请填写承包商、队伍名称和报备日期')
    return
  }
  if (!Object.values(capabilityForm).some(Boolean)) {
    ElMessage.warning('请至少选择一项施工能力')
    return
  }
  saving.value = true
  try {
    await createContractor({
      ...contractorForm,
      capability_tags: Object.fromEntries(capabilityOptions.map((item) => [item.key, capabilityForm[item.key]]))
    })
    ElMessage.success('异常补录已保存')
    supplementVisible.value = false
    await loadContractors()
  } catch (error) {
    showRequestError(error, '异常补录保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await Promise.all(canViewGlobalSync.value ? [loadSummary(), loadContractors(), loadLogs()] : [loadContractors()])
})
</script>

<style scoped>
.sync-strip,
.toolbar,
.table-panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 14px;
}

.sync-strip {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.sync-main,
.sync-state,
.sync-actions,
.sync-stats {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sync-main {
  flex-wrap: wrap;
}

.sync-state p,
.panel-head span {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.state-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #ef4444;
}

.state-dot.ok {
  background: #22c55e;
}

.state-dot.unset {
  background: #f59e0b;
}

.sync-stats span,
.muted {
  color: #6b7280;
  font-size: 13px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.metric-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px;
}

.metric-card span {
  display: block;
  color: #6b7280;
  font-size: 13px;
}

.metric-card strong {
  display: block;
  margin-top: 8px;
  font-size: 24px;
  color: #111827;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}

.panel-head h2 {
  margin: 0;
  font-size: 18px;
}

.tag-gap {
  margin: 2px 4px 2px 0;
}

.capacity-snapshot-table {
  width: 100%;
}

.capacity-snapshot-table :deep(.el-table__cell .cell) {
  width: max-content;
  min-width: 100%;
  white-space: nowrap;
}

.capability-tags {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.capability-tags .tag-gap {
  margin: 0;
}

.team-cell {
  display: grid;
  gap: 4px;
  width: max-content;
  white-space: nowrap;
}

.team-cell strong,
.team-cell span {
  white-space: nowrap;
}

.team-cell strong {
  color: #111827;
  font-weight: 600;
}

.team-cell span {
  color: #6b7280;
  font-size: 13px;
}

.row-actions {
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: 10px;
  line-height: 1.6;
  white-space: nowrap;
}

.row-actions :deep(.el-button),
.row-actions :deep(.el-dropdown) {
  margin-left: 0;
  padding: 0;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.exception-actions {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}

.exception-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.exception-buttons :deep(.el-button) {
  min-width: 96px;
  margin-left: 0;
}

.capability-switches {
  display: grid;
  grid-template-columns: repeat(3, minmax(96px, 1fr));
  gap: 8px 14px;
  width: 100%;
}

.capability-switches :deep(.el-checkbox) {
  margin-right: 0;
}

@media (max-width: 1180px) {
  .sync-strip {
    align-items: flex-start;
    flex-direction: column;
  }

  .metric-grid {
    grid-template-columns: repeat(3, minmax(120px, 1fr));
  }
}
</style>
