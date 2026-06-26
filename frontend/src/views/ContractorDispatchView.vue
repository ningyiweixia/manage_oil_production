<template>
  <section class="toolbar">
    <el-form :model="contractorQuery" inline>
      <el-form-item label="承包商">
        <el-input v-model="contractorQuery.contractor_name" clearable placeholder="输入承包商名称" />
      </el-form-item>
      <el-form-item label="队伍状态">
        <el-select v-model="contractorQuery.status" clearable placeholder="全部" style="width: 150px">
          <el-option label="可用" value="AVAILABLE" />
          <el-option label="忙碌" value="BUSY" />
          <el-option label="离线" value="OFFLINE" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadAll">查询</el-button>
        <el-button :icon="Plus" @click="openContractor">运力报备</el-button>
        <el-button :icon="DocumentAdd" @click="openSheet">创建运行表</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="split-grid">
    <article class="table-panel">
      <div class="panel-head">
        <div>
          <h2>承包商运力</h2>
          <p>维护每日队伍状态和施工能力标签。</p>
        </div>
      </div>
      <el-table v-loading="loading" :data="contractors" row-key="id">
        <el-table-column prop="contractor_name" label="承包商" min-width="140" />
        <el-table-column prop="team_name" label="队伍" min-width="120" />
        <el-table-column prop="report_date" label="日期" width="120" />
        <el-table-column prop="available_count" label="可用数" width="84" />
        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <el-tag :type="contractorTag(row.status)">{{ contractorStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="能力标签" min-width="180">
          <template #default="{ row }">
            <el-tag v-for="(value, key) in row.capability_tags" :key="key" class="tag-gap" effect="plain">
              {{ key }}: {{ value }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </article>

    <article class="table-panel">
      <div class="panel-head">
        <div>
          <h2>待派工运行表</h2>
          <p>按审批通过时间和产量优先级排序。</p>
        </div>
        <el-button :icon="Refresh" @click="loadPriority">刷新</el-button>
      </div>
      <el-table v-loading="loading" :data="prioritySheets" row-key="id">
        <el-table-column prop="operation_no" label="作业编号" min-width="180" />
        <el-table-column prop="project_id" label="项目ID" width="90" />
        <el-table-column label="进度" width="120">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="8" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="110">
          <template #default="{ row }">
            <el-button text type="primary" @click="openDispatch(row)">派工</el-button>
          </template>
        </el-table-column>
      </el-table>
    </article>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>修井运行表</h2>
        <p>跟踪派工状态、施工进度和 A5 回调结果。</p>
      </div>
    </div>
    <el-table v-loading="loading" :data="sheets" row-key="id">
      <el-table-column prop="operation_no" label="作业编号" min-width="180" />
      <el-table-column prop="project_id" label="项目ID" width="90" />
      <el-table-column prop="contractor_capacity_id" label="队伍ID" width="90" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="sheetTag(row.status)">{{ sheetStatusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="进度" min-width="160">
        <template #default="{ row }">
          <el-progress :percentage="row.progress" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button text type="primary" @click="openProgress(row)">更新进度</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>

  <el-dialog v-model="contractorVisible" title="运力报备" width="620px">
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
        </el-select>
      </el-form-item>
      <el-form-item label="大修资质"><el-switch v-model="majorRepair" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="contractorVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveContractor">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="sheetVisible" title="创建修井运行表" width="520px">
    <el-form :model="sheetForm" label-width="104px">
      <el-form-item label="项目ID"><el-input-number v-model="sheetForm.project_id" :min="1" /></el-form-item>
      <el-form-item label="计划开始"><el-date-picker v-model="sheetForm.planned_start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ" /></el-form-item>
      <el-form-item label="计划结束"><el-date-picker v-model="sheetForm.planned_end_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ssZ" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="sheetVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveSheet">创建</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="dispatchVisible" title="派工" width="520px">
    <el-form label-width="104px">
      <el-form-item label="运行表">
        <el-input :model-value="dispatchTarget?.operation_no" disabled />
      </el-form-item>
      <el-form-item label="选择队伍">
        <el-select v-model="dispatchContractorId" filterable placeholder="选择可用队伍" style="width: 100%">
          <el-option
            v-for="item in availableContractors"
            :key="item.id"
            :label="`${item.contractor_name} / ${item.team_name}`"
            :value="item.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dispatchVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="confirmDispatch">确认派工</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="progressVisible" title="更新进度" width="480px">
    <el-slider v-model="progressValue" :max="100" show-input />
    <template #footer>
      <el-button @click="progressVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveProgress">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { DocumentAdd, Plus, Refresh, Search } from '@element-plus/icons-vue'
import {
  createContractor,
  createOperationSheet,
  dispatchOperation,
  listContractors,
  listOperationSheets,
  listPrioritySheets,
  updateOperationProgress,
  type ContractorCapacity,
  type ContractorQuery,
  type OperationSheet
} from '../api/contractor'

const contractorStatusText = { AVAILABLE: '可用', BUSY: '忙碌', OFFLINE: '离线' }
const sheetStatusText = { WAITING_DISPATCH: '待派工', DISPATCHED: '已派工', WORKING: '施工中', FINISHED: '已完成', CANCELED: '已取消' }
const loading = ref(false)
const saving = ref(false)
const contractors = ref<ContractorCapacity[]>([])
const prioritySheets = ref<OperationSheet[]>([])
const sheets = ref<OperationSheet[]>([])
const contractorQuery = reactive<ContractorQuery>({ page: 1, page_size: 50, status: '' })
const contractorVisible = ref(false)
const sheetVisible = ref(false)
const dispatchVisible = ref(false)
const progressVisible = ref(false)
const dispatchTarget = ref<OperationSheet | null>(null)
const progressTarget = ref<OperationSheet | null>(null)
const dispatchContractorId = ref<number>()
const progressValue = ref(0)
const majorRepair = ref(false)
const contractorForm = reactive({
  contractor_name: '',
  team_name: '',
  report_date: new Date().toISOString().slice(0, 10),
  available_count: 1,
  status: 'AVAILABLE' as const,
  capability_tags: {}
})
const sheetForm = reactive<{ project_id: number; planned_start_at?: string; planned_end_at?: string }>({ project_id: 1 })
const availableContractors = computed(() => contractors.value.filter((item) => item.status === 'AVAILABLE'))

function contractorTag(status: string) {
  return status === 'AVAILABLE' ? 'success' : status === 'BUSY' ? 'warning' : 'info'
}

function sheetTag(status: string) {
  return status === 'FINISHED' ? 'success' : status === 'CANCELED' ? 'danger' : status === 'WAITING_DISPATCH' ? 'warning' : 'primary'
}

function contractorStatusLabel(status: keyof typeof contractorStatusText) {
  return contractorStatusText[status] || status
}

function sheetStatusLabel(status: keyof typeof sheetStatusText) {
  return sheetStatusText[status] || status
}

async function loadAll() {
  loading.value = true
  try {
    const [contractorPage, sheetPage, priority] = await Promise.all([
      listContractors(contractorQuery),
      listOperationSheets({ page: 1, page_size: 100 }),
      listPrioritySheets()
    ])
    contractors.value = contractorPage.items
    sheets.value = sheetPage.items
    prioritySheets.value = priority
  } finally {
    loading.value = false
  }
}

async function loadPriority() {
  prioritySheets.value = await listPrioritySheets()
}

function openContractor() {
  contractorVisible.value = true
}

function openSheet() {
  sheetVisible.value = true
}

function openDispatch(row: OperationSheet) {
  dispatchTarget.value = row
  dispatchContractorId.value = availableContractors.value[0]?.id
  dispatchVisible.value = true
}

function openProgress(row: OperationSheet) {
  progressTarget.value = row
  progressValue.value = row.progress
  progressVisible.value = true
}

async function saveContractor() {
  saving.value = true
  try {
    await createContractor({
      ...contractorForm,
      capability_tags: { major_repair: majorRepair.value }
    })
    ElMessage.success('运力已报备')
    contractorVisible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function saveSheet() {
  saving.value = true
  try {
    await createOperationSheet(sheetForm)
    ElMessage.success('运行表已创建')
    sheetVisible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function confirmDispatch() {
  if (!dispatchTarget.value || !dispatchContractorId.value) return
  saving.value = true
  try {
    await dispatchOperation({ operation_sheet_id: dispatchTarget.value.id, contractor_capacity_id: dispatchContractorId.value })
    ElMessage.success('派工成功')
    dispatchVisible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function saveProgress() {
  if (!progressTarget.value) return
  saving.value = true
  try {
    await updateOperationProgress(progressTarget.value.id, { progress: progressValue.value, progress_detail: { source: 'manual' } })
    ElMessage.success('进度已更新')
    progressVisible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

onMounted(loadAll)
</script>
