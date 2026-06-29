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
      <el-table-column prop="block_name" label="区块" min-width="110" />
      <el-table-column prop="report_unit" label="提报单位" min-width="120" />
      <el-table-column prop="production_priority" label="优先级" min-width="96" sortable>
        <template #default="{ row }">
          <el-progress :percentage="row.production_priority" :stroke-width="8" :show-text="false" />
        </template>
      </el-table-column>
      <el-table-column label="措施内容" min-width="190">
        <template #default="{ row }">
          <el-tag v-for="measure in row.measures_jsonb.measures || []" :key="measure.measure_type" class="tag-gap" effect="plain">
            {{ measureLabel(measure.measure_type) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="审批状态" min-width="280">
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
          <el-button v-if="hasPermission('workover_project_pool:update')" text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="row.status === 'REJECTED' && hasPermission('workover_project_pool:submit')" text type="success" @click="resubmitRejected(row)">重新提报</el-button>
          <el-button v-else-if="hasPermission('workover_project_pool:approve')" text type="success" :disabled="!canApprove(row.status)" @click="openApproval(row, 'APPROVED')">通过</el-button>
          <el-button v-if="row.status !== 'REJECTED' && hasPermission('workover_project_pool:approve')" text type="warning" :disabled="!canApprove(row.status)" @click="openApproval(row, 'REJECTED')">驳回</el-button>
          <el-button v-if="hasPermission('workover_project_pool:delete')" text type="danger" @click="confirmDelete(row)">删除</el-button>
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

  <el-dialog v-model="formVisible" :title="dialogTitle" width="820px">
    <el-form ref="projectFormRef" :model="projectForm" :rules="projectRules" label-width="104px">
      <el-row :gutter="16">
        <el-col :span="8"><el-form-item label="井号" prop="well_no"><el-input v-model="projectForm.well_no" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="井名"><el-input v-model="projectForm.well_name" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="层位"><el-input v-model="projectForm.layer" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="提报单位" prop="report_unit"><el-input v-model="projectForm.report_unit" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="属地单位"><el-input v-model="projectForm.territory_unit" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="区块"><el-input v-model="projectForm.block_name" /></el-form-item></el-col>
        <el-col :span="24"><el-form-item label="故障描述"><el-input v-model="projectForm.fault_description" type="textarea" :rows="2" /></el-form-item></el-col>
        <el-col :span="16"><el-form-item label="上修原因"><el-input v-model="projectForm.reason" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="优先级"><el-slider v-model="projectForm.production_priority" :max="100" /></el-form-item></el-col>
      </el-row>

      <div class="measure-head">
        <strong>措施 JSONB 表单</strong>
        <el-button size="small" :icon="Plus" @click="addMeasure">新增措施</el-button>
      </div>
      <div v-for="(measure, index) in projectForm.measures_jsonb.measures" :key="index" class="measure-row">
        <el-select v-model="measure.measure_type" placeholder="措施类型" filterable clearable>
          <el-option v-for="opt in measureTypeOptions" :key="opt.item_value" :label="opt.item_label" :value="opt.item_value" />
        </el-select>
        <el-input v-model="measure.process" placeholder="施工工序" />
        <el-input-number v-model="measure.duration_days" :min="0" placeholder="天数" />
        <el-input-number v-model="measure.estimated_cost" :min="0" :precision="1" placeholder="费用(万元)" />
        <el-button :icon="Delete" circle @click="removeMeasure(index)" />
      </div>
    </el-form>
    <template #footer>
      <el-button @click="formVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveProject">保存</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="approvalDialogVisible" title="审批处理" width="520px">
    <el-form label-position="top">
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
      确认要删除项目 <strong>{{ deleteTarget.well_no }}</strong>（{{ deleteTarget.well_name || '未命名' }}）吗？删除后项目将标记为已作废，可在数据库中恢复。
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
import { createProject, deleteProject, getProjectAnalytics, listProjects, patchProjectStatus, submitProjects, updateProject } from '../api/workover'
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
  DISPATCHED: 0,
  VOIDED: 0
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

const projectForm = reactive<Omit<WorkoverProject, 'id' | 'created_at' | 'updated_at'>>({
  well_no: '',
  well_name: '',
  layer: '',
  fault_description: '',
  territory_unit: '',
  block_name: '',
  report_unit: '',
  production_priority: 60,
  status: 'DRAFT',
  reason: '',
  measures_jsonb: { measures: [] },
  remark: ''
})

const projectRules: FormRules = {
  well_no: [{ required: true, message: '请输入井号', trigger: 'blur' }],
  report_unit: [{ required: true, message: '请输入提报单位', trigger: 'blur' }]
}

const dialogTitle = computed(() => {
  if (!editingProject.value) return '新增上修提报'
  if (editingProject.value.status === 'REJECTED') return '修改已驳回项目（保存后回到草稿）'
  return '编辑项目池井号'
})

const workflowNodes = computed(() => [
  { code: '', label: '全部项目', desc: '项目总览', count: totalProjectCount.value },
  { code: 'DRAFT', label: '基层提报', desc: '项目池录入', count: countStatus('DRAFT') },
  { code: 'PENDING_GEOLOGY_VERIFY', label: '地质核实', desc: '产量与油藏核实', count: countStatus('PENDING_GEOLOGY_VERIFY') },
  { code: 'PENDING_PROCESS_VERIFY', label: '工艺核实', desc: '井况与可行性', count: countStatus('PENDING_PROCESS_VERIFY') },
  { code: 'APPROVED', label: '入运行库', desc: '等待派工', count: countStatus('APPROVED') },
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
    DISPATCHED: 0,
    VOIDED: 0
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
    layer: '',
    fault_description: '',
    territory_unit: '',
    block_name: '',
    report_unit: '',
    production_priority: 60,
    status: 'DRAFT',
    reason: '',
    measures_jsonb: { measures: [{ measure_type: '', process: '', construction_params: {}, duration_days: 0, estimated_cost: 0 }] },
    remark: ''
  })
}

function openCreate() {
  editingProject.value = null
  resetForm()
  loadMeasureTypes()
  formVisible.value = true
}

function openEdit(row: WorkoverProject) {
  editingProject.value = row
  Object.assign(projectForm, JSON.parse(JSON.stringify(row)))
  // 编辑已驳回项目时，保存后自动设为草稿以便重新提报
  if (row.status === 'REJECTED') {
    projectForm.status = 'DRAFT'
  }
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

async function saveProject() {
  try {
    await projectFormRef.value?.validate()
  } catch {
    // 表单校验不通过，Element Plus 会自动提示
    return
  }
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
  approvalComment.value = status === 'APPROVED'
    ? nextStatus === 'APPROVED'
      ? '核实通过，同意通过审批，进入运行库。'
      : `核实通过，同意流转至「${statusLabels[nextStatus]}」。`
    : '资料需补充，退回修改。'
  approvalDialogVisible.value = true
}

async function confirmApproval() {
  if (!pendingApproval.value) return
  saving.value = true
  try {
    await patchProjectStatus(pendingApproval.value.id, pendingApproval.value.status, approvalComment.value)
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
    ElMessage.success('项目已删除（已作废）')
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
