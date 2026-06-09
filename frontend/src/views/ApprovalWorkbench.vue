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
        <el-input v-model="query.measure_type" clearable placeholder="检泵/酸化" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadProjects">查询</el-button>
        <el-button :icon="Plus" @click="openCreate">新增提报</el-button>
        <el-button :icon="TrendCharts" @click="openDashboard">查看大屏</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="workflow-strip">
    <div v-for="node in workflowNodes" :key="node.code" class="workflow-node clickable" @click="filterByStatus(node.code)">
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
      <el-button type="success" :disabled="!selectedIds.length" :icon="Promotion" @click="submitDialogVisible = true">批量提交</el-button>
    </div>

    <el-table v-loading="loading" :data="projects" row-key="id" @selection-change="onSelectionChange">
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
            {{ measure.measure_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="审批状态" min-width="210">
        <template #default="{ row }">
          <el-steps :active="statusStep(row.status)" finish-status="success" simple class="mini-steps">
            <el-step title="提报" />
            <el-step title="地质" />
            <el-step title="工艺" />
            <el-step title="入库" />
          </el-steps>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="220" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button text type="success" :disabled="!canApprove(row.status)" @click="openApproval(row, 'APPROVED')">通过</el-button>
          <el-button text type="warning" :disabled="!canApprove(row.status)" @click="openApproval(row, 'REJECTED')">驳回</el-button>
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

  <el-dialog v-model="formVisible" :title="editingProject ? '编辑项目池井号' : '新增上修提报'" width="820px">
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
        <el-input v-model="measure.measure_type" placeholder="措施类型" />
        <el-input v-model="measure.process" placeholder="施工工序" />
        <el-input-number v-model="measure.duration_days" :min="0" placeholder="天数" />
        <el-input-number v-model="measure.estimated_cost" :min="0" :precision="1" placeholder="费用" />
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
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage, ElNotification } from 'element-plus'
import { Delete, Plus, Promotion, Search, TrendCharts } from '@element-plus/icons-vue'
import { createProject, listProjects, patchProjectStatus, submitProjects, updateProject } from '../api/workover'
import { canApprove, nextApprovedStatus, statusLabels, statusStep } from '../utils/status'
import { emitProjectDataChanged } from '../composables/useProjectSync'
import type { ProjectPoolStatus, ProjectQuery, WorkoverProject } from '../types/workover'

const statusOptions = [
  'DRAFT',
  'PENDING_GEOLOGY_VERIFY',
  'PENDING_PROCESS_VERIFY',
  'APPROVED',
  'REJECTED',
  'DISPATCHED',
  'VOIDED'
].map((value) => ({ label: statusLabels[value as ProjectPoolStatus], value }))

const route = useRoute()
const router = useRouter()
const query = reactive<ProjectQuery>({ page: 1, page_size: 10, status: '' })
const projects = ref<WorkoverProject[]>([])
const total = ref(0)
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
const projectFormRef = ref<FormInstance>()

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

const workflowNodes = computed(() => [
  { code: 'DRAFT', label: '基层提报', desc: '项目池录入', count: countStatus('DRAFT') },
  { code: 'PENDING_GEOLOGY_VERIFY', label: '地质核实', desc: '产量与油藏核实', count: countStatus('PENDING_GEOLOGY_VERIFY') },
  { code: 'PENDING_PROCESS_VERIFY', label: '工艺核实', desc: '井况与可行性', count: countStatus('PENDING_PROCESS_VERIFY') },
  { code: 'APPROVED', label: '入运行库', desc: '等待派工', count: countStatus('APPROVED') }
])

function countStatus(status: ProjectPoolStatus) {
  return projects.value.filter((item) => item.status === status).length
}

async function loadProjects() {
  loading.value = true
  try {
    const result = await listProjects(query)
    projects.value = result.items
    total.value = result.total
  } finally {
    loading.value = false
  }
}

function filterByStatus(status: string) {
  query.status = status as ProjectPoolStatus
  query.page = 1
  router.replace({ path: '/approval', query: { status } })
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
  formVisible.value = true
}

function openEdit(row: WorkoverProject) {
  editingProject.value = row
  Object.assign(projectForm, JSON.parse(JSON.stringify(row)))
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
  await projectFormRef.value?.validate()
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
    await loadProjects()
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
    await loadProjects()
  } finally {
    saving.value = false
  }
}

function openApproval(row: WorkoverProject, status: ProjectPoolStatus) {
  const nextStatus = status === 'APPROVED' ? nextApprovedStatus(row.status) : status
  pendingApproval.value = { id: row.id, status: nextStatus }
  approvalComment.value = status === 'APPROVED'
    ? `核实通过，同意流转至「${statusLabels[nextStatus]}」。`
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
    await loadProjects()
  } finally {
    saving.value = false
  }
}

watch(
  () => route.query.status,
  (status) => {
    if (typeof status === 'string' && status !== query.status) {
      query.status = status as ProjectPoolStatus
      query.page = 1
      loadProjects()
    }
  }
)

onMounted(() => {
  if (typeof route.query.status === 'string') {
    query.status = route.query.status as ProjectPoolStatus
  }
  loadProjects()
})
</script>
