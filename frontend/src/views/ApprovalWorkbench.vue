<template>
  <section class="toolbar">
    <el-form :model="query" inline>
      <el-form-item label="井号">
        <el-input v-model="query.well_no" clearable placeholder="CY2-136" />
      </el-form-item>
      <el-form-item label="区块">
        <el-input v-model="query.block_name" clearable placeholder="北一区" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="query.status" clearable placeholder="全部" style="width: 190px">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="措施">
        <el-select v-model="query.measure_type" clearable filterable placeholder="全部措施类型" style="width: 180px">
          <el-option v-for="opt in measureTypeOptions" :key="opt.item_value" :label="opt.item_label" :value="opt.item_value" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadProjects">查询</el-button>
        <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        <el-button v-if="hasPermission('workover_project_pool:create')" :icon="Plus" @click="openCreate">新增提报</el-button>
        <el-button :icon="TrendCharts" @click="openDashboard">查看大屏</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="workflow-strip">
    <div
      v-for="node in workflowNodes"
      :key="node.code || 'ALL'"
      class="workflow-node clickable"
      :class="{ active: (query.status || '') === node.code }"
      @click="filterByStatus(node.code)"
    >
      <span>{{ node.count }}</span>
      <strong>{{ node.label }}</strong>
      <small>{{ node.desc }}</small>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>项目池与审批流转</h2>
        <p>勾选草稿可批量提交；待审核节点可在线通过、驳回或退回补充。</p>
      </div>
      <el-button v-if="hasPermission('workover_project_pool:submit')" type="success" :disabled="!selectedIds.length" :icon="Promotion" @click="submitDialogVisible = true">批量提交</el-button>
    </div>

    <el-table v-loading="loading" :data="projects" row-key="id" empty-text="暂无符合条件的项目" @selection-change="onSelectionChange">
      <el-table-column type="selection" width="48" />
      <el-table-column prop="well_no" label="井号" min-width="110" fixed />
      <el-table-column prop="well_type" label="井别" min-width="80" />
      <el-table-column prop="block_name" label="区块" min-width="110" />
      <el-table-column prop="county" label="县区" min-width="80" />
      <el-table-column prop="initiator_name" label="发起人" min-width="90" />
      <el-table-column prop="initiator_phone" label="联系电话" min-width="120" />
      <el-table-column prop="report_unit" label="提报单位" min-width="120" />
      <el-table-column prop="production_priority" label="优先级" min-width="96" sortable>
        <template #default="{ row }">
          <el-progress :percentage="row.production_priority" :stroke-width="8" :show-text="false" />
        </template>
      </el-table-column>
      <el-table-column label="核实产量" min-width="110">
        <template #default="{ row }">
          <span>{{ row.geology_verified_daily_oil ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="工艺结论" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag v-if="row.process_can_workover === true" type="success" effect="plain">可上修</el-tag>
          <el-tag v-else-if="row.process_can_workover === false" type="danger" effect="plain">不可上修</el-tag>
          <span v-else class="muted-text">待核实</span>
          <span v-if="row.process_well_condition" class="condition-text">{{ row.process_well_condition }}</span>
        </template>
      </el-table-column>
      <el-table-column label="措施内容" min-width="190">
        <template #default="{ row }">
          <el-tag v-for="measure in row.measures_jsonb.measures || []" :key="measure.measure_type" class="tag-gap" effect="plain">
            {{ measureLabel(measure.measure_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="审批状态" min-width="340">
        <template #default="{ row }">
          <div class="approval-status-cell">
            <el-tag :type="statusTagType(row.status)" effect="light" round>
              {{ row.status === 'REJECTED' ? rejectedAtLabel(row.rejected_from_status) : statusLabel(row.status) }}
            </el-tag>
            <div v-if="showApprovalFlow(row.status)" class="approval-flow">
              <span
                v-for="node in approvalFlowNodes"
                :key="node.status"
                class="approval-flow-node"
                :class="approvalNodeClass(row.status, node.status, row.rejected_from_status)"
              >
                <i></i>
                <b>{{ node.label }}</b>
              </span>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="260" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button v-if="hasPermission('workover_project_pool:update')" text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="row.status === 'REJECTED' && hasPermission('workover_project_pool:submit')" text type="success" @click="resubmitRejected(row)">重新提报</el-button>
            <el-button v-else-if="hasPermission('workover_project_pool:approve')" text type="success" :disabled="!canApprove(row.status)" @click="openApproval(row, 'APPROVED')">通过</el-button>
            <el-button v-if="row.status !== 'REJECTED' && hasPermission('workover_project_pool:approve')" text type="warning" :disabled="!canApprove(row.status)" @click="openApproval(row, 'REJECTED')">驳回</el-button>
            <el-button v-if="hasPermission('workover_project_pool:delete')" text type="danger" @click="confirmDelete(row)">删除</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="query.page"
      v-model:page-size="query.page_size"
      class="pager"
      layout="total, sizes, prev, pager, next"
      :total="total"
      @change="loadProjects"
    />
  </section>

  <el-dialog v-model="formVisible" :title="dialogTitle" width="960px" class="project-dialog">
    <el-form ref="projectFormRef" :model="projectForm" :rules="projectRules" label-width="96px">
      <div class="form-section-title">基础信息</div>
      <el-row :gutter="16">
        <el-col :span="8"><el-form-item label="井号" prop="well_no"><el-input v-model="projectForm.well_no" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="井名"><el-input v-model="projectForm.well_name" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="层位"><el-input v-model="projectForm.layer" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="提报单位" prop="report_unit"><el-input v-model="projectForm.report_unit" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="属地单位"><el-input v-model="projectForm.territory_unit" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="区块"><el-input v-model="projectForm.block_name" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="井别">
          <el-select v-model="projectForm.well_type" placeholder="请选择" clearable>
            <el-option label="油井" value="油井" />
            <el-option label="水井" value="水井" />
            <el-option label="注气井" value="注气井" />
          </el-select>
        </el-form-item></el-col>
        <el-col :span="8"><el-form-item label="县区"><el-input v-model="projectForm.county" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="发起人"><el-input v-model="projectForm.initiator_name" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="联系电话"><el-input v-model="projectForm.initiator_phone" /></el-form-item></el-col>
        <el-col :span="24"><el-form-item label="故障描述"><el-input v-model="projectForm.fault_description" type="textarea" :rows="2" /></el-form-item></el-col>
        <el-col :span="16"><el-form-item label="上修原因" prop="reason"><el-input v-model="projectForm.reason" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="优先级"><el-slider v-model="projectForm.production_priority" :max="100" /></el-form-item></el-col>
      </el-row>

      <div class="measure-head">
        <strong>修井措施</strong>
        <el-button size="small" :icon="Plus" @click="addMeasure">新增措施</el-button>
      </div>
      <div v-for="(measure, index) in projectForm.measures_jsonb.measures" :key="index" class="measure-row">
        <div class="measure-field">
          <label>措施类型</label>
          <el-select v-model="measure.measure_type" placeholder="请选择" filterable clearable>
            <el-option v-for="opt in measureTypeOptions" :key="opt.item_value" :label="opt.item_label" :value="opt.item_value" />
          </el-select>
        </div>
        <div class="measure-field">
          <label>施工工序</label>
          <el-input v-model="measure.process" placeholder="如冲砂、检泵" />
        </div>
        <div class="measure-field">
          <label>预计工期(天)</label>
          <el-input-number v-model="measure.duration_days" :min="0" :controls="false" />
        </div>
        <div class="measure-field">
          <label>估算费用(万元)</label>
          <el-input-number v-model="measure.estimated_cost" :min="0" :precision="1" :controls="false" />
        </div>
        <el-button class="measure-delete" :icon="Delete" circle @click="removeMeasure(index)" />
      </div>

      <div class="form-section-title" style="margin-top:16px">附件信息</div>
      <el-row :gutter="16">
        <el-col :span="24"><el-form-item label="照片附件">
          <el-input v-model="photoUrlsText" type="textarea" :rows="2" placeholder="输入照片URL，多个地址用逗号分隔" />
          <div v-if="projectForm.photo_urls && projectForm.photo_urls.length" style="margin-top:4px;color:#909399;font-size:12px">
            已添加 {{ projectForm.photo_urls.length }} 个附件
          </div>
        </el-form-item></el-col>
      </el-row>
    </el-form>
    <template #footer>
      <el-button @click="formVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveProject">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="approvalDialogVisible" title="审批处理" width="520px">
    <el-form label-position="top">
      <el-form-item v-if="approvalTargetStatus === 'PENDING_PROCESS_VERIFY'" label="核实日产油">
        <el-input-number v-model="approvalExtra.geology_verified_daily_oil" :min="0" :precision="2" :controls="false" style="width: 220px" />
      </el-form-item>
      <template v-if="approvalTargetStatus === 'APPROVED' || approvalTargetStatus === 'REJECTED'">
        <el-form-item label="井况核实结论">
          <el-input v-model="approvalExtra.process_well_condition" type="textarea" :rows="3" placeholder="填写井筒、管柱、套损、施工风险等核实结论" />
        </el-form-item>
        <el-form-item label="是否可以上修">
          <el-switch v-model="approvalExtra.process_can_workover" />
        </el-form-item>
      </template>
      <el-form-item label="处理意见">
        <el-input v-model="approvalComment" type="textarea" :rows="4" placeholder="请填写核实结论、退回原因或补充说明" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="approvalDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="confirmApproval">确认流转</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="submitDialogVisible" title="批量提交至地质核实" width="520px">
    <el-input v-model="submitComment" type="textarea" :rows="4" placeholder="提交说明" />
    <template #footer>
      <el-button @click="submitDialogVisible = false">取消</el-button>
      <el-button type="success" :loading="saving" @click="confirmSubmit">提交</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="deleteDialogVisible" title="删除项目" width="440px">
    <p v-if="deleteTarget">
      确认要删除项目 <strong>{{ deleteTarget.well_no }}</strong>（{{ deleteTarget.well_name || '未命名' }}）吗？删除后项目将从列表中移除，可在数据库中恢复。
    </p>
    <template #footer>
      <el-button @click="deleteDialogVisible = false">取消</el-button>
      <el-button type="danger" :loading="saving" @click="confirmDeleteAction">确认删除</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Delete, Plus, Promotion, Refresh, Search, TrendCharts } from '@element-plus/icons-vue'
import { createProject, deleteProject, getProjectAnalytics, listProjects, patchProjectStatus, submitProjects, updateProject, type WorkoverProjectPayload } from '../api/workover'
import { listDictionaryItems, type DictionaryItem } from '../api/dictionary'
import { approvalFlowNodes, approvalNodeClass, canApprove, nextApprovedStatus, rejectedAtLabel, showApprovalFlow, statusLabels, statusTagType } from '../utils/status'
import { emitProjectDataChanged, useProjectDataChanged } from '../composables/useProjectSync'
import type { ProjectPoolStatus, ProjectQuery, WorkoverProject } from '../types/workover'

const statusOptions = (Object.keys(statusLabels) as ProjectPoolStatus[]).map((value) => ({
  label: statusLabels[value],
  value
}))

function userPermissions(): string[] {
  try { return JSON.parse(localStorage.getItem('permissions') || '[]') } catch { return [] }
}
function hasPermission(perm: string): boolean {
  return userPermissions().includes(perm)
}

const route = useRoute()
const router = useRouter()
const query = reactive<ProjectQuery>({ page: 1, page_size: 10, status: '' })
const projects = ref<WorkoverProject[]>([])
const total = ref(0)
const workflowCounts = ref<Record<ProjectPoolStatus, number>>({
  DRAFT: 0,
  PENDING_GEOLOGY_VERIFY: 0,
  PENDING_PROCESS_VERIFY: 0,
  APPROVED: 0,
  REJECTED: 0,
  DISPATCHED: 0
})
const loading = ref(false)
const saving = ref(false)
const selectedIds = ref<number[]>([])
const formVisible = ref(false)
const submitDialogVisible = ref(false)
const approvalDialogVisible = ref(false)
const editingProject = ref<WorkoverProject | null>(null)
const pendingApproval = ref<{ id: number; status: ProjectPoolStatus } | null>(null)
const submitComment = ref('')
const approvalComment = ref('')
const approvalExtra = reactive<{
  geology_verified_daily_oil?: number | string | null
  process_well_condition?: string | null
  process_can_workover?: boolean | null
}>({
  geology_verified_daily_oil: null,
  process_well_condition: '',
  process_can_workover: true
})
const deleteDialogVisible = ref(false)
const deleteTarget = ref<WorkoverProject | null>(null)
const projectFormRef = ref<FormInstance>()
const measureTypeOptions = ref<DictionaryItem[]>([])
const measureLabelMap = ref<Record<string, string>>({})

async function loadMeasureTypes() {
  try {
    const items = await listDictionaryItems('measure_type')
    measureTypeOptions.value = items
    // 构建 value → label 映射表，用于表格显示
    const map: Record<string, string> = {}
    for (const item of items) {
      if (!map[item.item_value] || item.item_label.length <= map[item.item_value].length) {
        map[item.item_value] = item.item_label
      }
    }
    measureLabelMap.value = map
  } catch {
    measureTypeOptions.value = []
    measureLabelMap.value = {}
  }
}

function measureLabel(value: string): string {
  return measureLabelMap.value[value] || value
}

const photoUrlsText = computed<string>({
  get() { return (projectForm.photo_urls || []).join(', ') },
  set(val: string) { projectForm.photo_urls = val ? val.split(',').map((s) => s.trim()).filter(Boolean) : [] }
})

const projectForm = reactive<WorkoverProjectPayload>({
  well_no: '',
  well_name: '',
  well_type: '',
  layer: '',
  fault_description: '',
  territory_unit: '',
  block_name: '',
  county: '',
  report_unit: '',
  initiator_name: '',
  initiator_phone: '',
  production_priority: 60,
  reason: '',
  measures_jsonb: { measures: [] },
  photo_urls: [],
  remark: ''
})

const approvalTargetStatus = computed(() => pendingApproval.value?.status || '')

const projectRules: FormRules = {
  well_no: [{ required: true, message: '请输入井号', trigger: 'blur' }],
  report_unit: [{ required: true, message: '请输入提报单位', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入上修原因', trigger: 'blur' }]
}

const dialogTitle = computed(() => {
  if (!editingProject.value) return '新增上修提报'
  if (editingProject.value.status === 'REJECTED') return '修改已驳回项目'
  return '编辑项目池井号'
})

const workflowNodes = computed(() => [
  { code: '', label: '全部项目', desc: '项目总览', count: totalProjectCount.value },
  { code: 'DRAFT', label: '基层提报', desc: '项目池录入', count: countStatus('DRAFT') },
  { code: 'PENDING_GEOLOGY_VERIFY', label: '地质核实', desc: '产量与油藏核实', count: countStatus('PENDING_GEOLOGY_VERIFY') },
  { code: 'PENDING_PROCESS_VERIFY', label: '工艺核实', desc: '井况与可行性', count: countStatus('PENDING_PROCESS_VERIFY') },
  { code: 'APPROVED', label: '已入库', desc: '等待派工', count: countStatus('APPROVED') },
  { code: 'DISPATCHED', label: '已派工', desc: '进入施工跟踪', count: countStatus('DISPATCHED') },
  { code: 'REJECTED', label: '已驳回', desc: '待补充修改', count: countStatus('REJECTED') }
])

function countStatus(status: ProjectPoolStatus) {
  return workflowCounts.value[status] || 0
}

const totalProjectCount = computed(() => Object.values(workflowCounts.value).reduce((sum, value) => sum + value, 0))

function statusLabel(status: ProjectPoolStatus) {
  return statusLabels[status]
}

async function reloadWorkbenchData() {
  await Promise.all([loadWorkflowCounts(), loadProjects()])
}

async function loadProjects() {
  loading.value = true
  try {
    const result = await listProjects(query)
    projects.value = result.items
    total.value = result.total
    selectedIds.value = []
  } finally {
    loading.value = false
  }
}

async function loadWorkflowCounts() {
  const summary = await getProjectAnalytics({})
  const nextCounts: Record<ProjectPoolStatus, number> = {
    DRAFT: 0,
    PENDING_GEOLOGY_VERIFY: 0,
    PENDING_PROCESS_VERIFY: 0,
    APPROVED: 0,
    REJECTED: 0,
    DISPATCHED: 0
  }
  summary.status_counts.forEach((item) => {
    nextCounts[item.status] = item.count
  })
  workflowCounts.value = nextCounts
}

function filterByStatus(status: string) {
  query.status = status ? status as ProjectPoolStatus : ''
  query.page = 1
  router.replace({ path: '/approval', query: status ? { status } : {} })
  loadProjects()
}

function resetQuery() {
  query.page = 1
  query.status = ''
  query.well_no = ''
  query.block_name = ''
  query.measure_type = ''
  router.replace({ path: '/approval' })
  loadProjects()
}

function openDashboard() {
  router.push({
    path: '/dashboard',
    query: {
      status: query.status || undefined,
      measure_type: query.measure_type || undefined,
      block_name: query.block_name || undefined
    }
  })
}

function resetForm() {
  Object.assign(projectForm, {
    well_no: '',
    well_name: '',
    well_type: '',
    layer: '',
    fault_description: '',
    territory_unit: '',
    block_name: '',
    county: '',
    report_unit: '',
    initiator_name: '',
    initiator_phone: '',
    production_priority: 60,
    reason: '',
    measures_jsonb: { measures: [{ measure_type: '', process: '', construction_params: {}, duration_days: 0, estimated_cost: 0 }] },
    photo_urls: [],
    remark: ''
  })
}

function toProjectPayload(row: WorkoverProject): WorkoverProjectPayload {
  return {
    well_no: row.well_no,
    well_name: row.well_name || '',
    well_type: row.well_type || '',
    layer: row.layer || '',
    fault_description: row.fault_description || '',
    territory_unit: row.territory_unit || '',
    block_name: row.block_name || '',
    county: row.county || '',
    report_unit: row.report_unit,
    initiator_name: row.initiator_name || '',
    initiator_phone: row.initiator_phone || '',
    production_priority: row.production_priority,
    reason: row.reason || '',
    measures_jsonb: JSON.parse(JSON.stringify(row.measures_jsonb || { measures: [] })),
    photo_urls: [...(row.photo_urls || [])],
    remark: row.remark || ''
  }
}

function openCreate() {
  editingProject.value = null
  resetForm()
  loadMeasureTypes()
  formVisible.value = true
}

function openEdit(row: WorkoverProject) {
  editingProject.value = row
  Object.assign(projectForm, toProjectPayload(row))
  loadMeasureTypes()
  formVisible.value = true
}

function addMeasure() {
  projectForm.measures_jsonb.measures = projectForm.measures_jsonb.measures || []
  projectForm.measures_jsonb.measures.push({ measure_type: '', process: '', construction_params: {}, duration_days: 0, estimated_cost: 0 })
}

function removeMeasure(index: number) {
  projectForm.measures_jsonb.measures?.splice(index, 1)
}

function validateMeasures() {
  const measures = projectForm.measures_jsonb.measures || []
  if (!measures.length) {
    ElMessage.warning('请至少新增一条修井措施')
    return false
  }
  const measureTypes = measures.map((measure) => measure.measure_type).filter(Boolean)
  if (measureTypes.length !== measures.length) {
    ElMessage.warning('请选择每条修井措施的措施类型')
    return false
  }
  if (new Set(measureTypes).size !== measureTypes.length) {
    ElMessage.warning('修井措施类型不能重复')
    return false
  }
  return true
}

async function saveProject() {
  try {
    await projectFormRef.value?.validate()
  } catch {
    // 表单校验不通过，Element Plus 会自动提示
    return
  }
  if (!validateMeasures()) return
  saving.value = true
  try {
    if (editingProject.value) {
      await updateProject(editingProject.value.id, projectForm)
    } else {
      await createProject(projectForm)
    }
    ElMessage.success('保存成功')
    formVisible.value = false
    emitProjectDataChanged()
    await loadWorkflowCounts()
    await loadProjects()
  } catch (error: any) {
    const msg = error?.response?.data?.msg || error?.message || '保存失败，请检查网络连接'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

function onSelectionChange(rows: WorkoverProject[]) {
  selectedIds.value = rows.map((row) => row.id)
}

async function confirmSubmit() {
  saving.value = true
  try {
    await submitProjects(selectedIds.value, submitComment.value)
    ElNotification.success({ title: '待办已推送', message: '已提交至地质核实节点' })
    submitDialogVisible.value = false
    emitProjectDataChanged()
    await loadWorkflowCounts()
    await loadProjects()
  } catch (error: any) {
    const msg = error?.response?.data?.msg || error?.message || '提交失败，请检查网络连接'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

function openApproval(row: WorkoverProject, status: ProjectPoolStatus) {
  const nextStatus = status === 'APPROVED' ? nextApprovedStatus(row.status) : status
  pendingApproval.value = { id: row.id, status: nextStatus }
  approvalExtra.geology_verified_daily_oil = null
  approvalExtra.process_well_condition = ''
  approvalExtra.process_can_workover = nextStatus === 'REJECTED' ? false : true
  approvalComment.value = status === 'APPROVED'
    ? nextStatus === 'APPROVED'
      ? '核实通过，同意通过审批，进入运行库。'
      : `核实通过，同意流转至「${statusLabels[nextStatus]}」。`
    : '资料需补充，退回修改。'
  approvalDialogVisible.value = true
}

async function confirmApproval() {
  if (!pendingApproval.value) return
  const verifiedDailyOil = approvalExtra.geology_verified_daily_oil ?? null
  const normalizedDailyOil =
    verifiedDailyOil === null || verifiedDailyOil === ''
      ? null
      : Number(verifiedDailyOil)
  if (
    pendingApproval.value.status === 'PENDING_PROCESS_VERIFY'
    && (normalizedDailyOil === null || Number.isNaN(normalizedDailyOil))
  ) {
    ElMessage.warning('请填写核实日产油')
    return
  }
  if (pendingApproval.value.status === 'APPROVED' && !approvalExtra.process_well_condition) {
    ElMessage.warning('请填写井况核实结论')
    return
  }
  saving.value = true
  try {
    await patchProjectStatus(pendingApproval.value.id, pendingApproval.value.status, approvalComment.value, {
      ...approvalExtra,
      geology_verified_daily_oil: normalizedDailyOil
    })
    ElMessage.success('审批状态已更新')
    approvalDialogVisible.value = false
    emitProjectDataChanged()
    await loadWorkflowCounts()
    await loadProjects()
  } catch (error: any) {
    const msg = error?.response?.data?.msg || error?.message || '审批操作失败，请检查网络连接'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

async function resubmitRejected(row: WorkoverProject) {
  // Smart routing: re-submit to the node where it was rejected, or default to geology
  const resubmitTo: ProjectPoolStatus =
    row.rejected_from_status === 'PENDING_PROCESS_VERIFY'
      ? 'PENDING_PROCESS_VERIFY'
      : 'PENDING_GEOLOGY_VERIFY'
  const targetName = resubmitTo === 'PENDING_PROCESS_VERIFY' ? '工艺核实' : '地质核实'
  try {
    await ElMessageBox.confirm(
      `将项目「${row.well_no}」修改后重新提交至「${targetName}」环节继续审批。`,
      '重新提报',
      { confirmButtonText: '确认提交', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // user cancelled
  }
  saving.value = true
  try {
    await patchProjectStatus(row.id, resubmitTo, '修改后重新提报')
    ElMessage.success(`已重新提交至${targetName}`)
    emitProjectDataChanged()
    await loadWorkflowCounts()
    await loadProjects()
  } catch (error: any) {
    const msg = error?.response?.data?.msg || error?.message || '重新提报失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

function confirmDelete(row: WorkoverProject) {
  deleteTarget.value = row
  deleteDialogVisible.value = true
}

async function confirmDeleteAction() {
  if (!deleteTarget.value) return
  saving.value = true
  try {
    await deleteProject(deleteTarget.value.id)
    ElMessage.success('项目已删除')
    deleteDialogVisible.value = false
    deleteTarget.value = null
    emitProjectDataChanged()
    await loadWorkflowCounts()
    await loadProjects()
  } catch (error: any) {
    const msg = error?.response?.data?.msg || error?.message || '删除失败，请检查网络连接'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

watch(
  () => route.query.status,
  (status) => {
    const nextStatus = typeof status === 'string' ? status as ProjectPoolStatus : ''
    if (nextStatus !== query.status) {
      query.status = nextStatus
      query.page = 1
      loadProjects()
    }
  }
)

useProjectDataChanged(() => {
  void reloadWorkbenchData()
})

onMounted(() => {
  if (typeof route.query.status === 'string') {
    query.status = route.query.status as ProjectPoolStatus
  }
  loadMeasureTypes()
  void reloadWorkbenchData()
})
</script>

<style scoped>
.condition-text {
  margin-left: 8px;
  color: #667085;
}
</style>
