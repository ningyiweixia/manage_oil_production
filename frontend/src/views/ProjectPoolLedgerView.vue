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
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadProjects">查询</el-button>
        <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>
    <div class="toolbar-actions">
      <el-button v-if="hasPermission('workover_project_pool:create')" :icon="Plus" @click="openCreate">新增提报</el-button>
      <el-upload :auto-upload="false" :show-file-list="false" accept=".xlsx,.xls" :on-change="handleImportSelected">
        <el-button v-if="hasPermission('workover_project_pool:import')" :icon="Upload">导入</el-button>
      </el-upload>
      <el-button v-if="hasPermission('workover_project_pool:import')" :icon="Download" @click="downloadTemplate">下载模板</el-button>
      <el-button v-if="hasPermission('workover_project_pool:export')" :icon="Download" @click="downloadExport">导出</el-button>
      <el-button v-if="hasPermission('workover_project_pool:submit')" type="success" :disabled="!selectedIds.length" :icon="Promotion" @click="submitDialogVisible = true">批量提交</el-button>
    </div>
  </section>

  <section class="source-summary">
    <div class="source-summary-item">
      <span>{{ totalProjectCount }}</span>
      <strong>项目总数</strong>
      <small>源头台账规模</small>
    </div>
    <div class="source-summary-item">
      <span>{{ countStatus('DRAFT') }}</span>
      <strong>草稿待提交</strong>
      <small>基层录入暂存</small>
    </div>
    <div class="source-summary-item">
      <span>{{ supplementCount }}</span>
      <strong>资料需补充</strong>
      <small>完整性待完善</small>
    </div>
    <div class="source-summary-item">
      <span>{{ duplicateCount }}</span>
      <strong>重复井提示</strong>
      <small>同井历史提报</small>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>项目池台账</h2>
        <p>聚焦上修源头台账、资料完整性、附件资料、导入导出和提交审批。</p>
      </div>
    </div>
    <el-table v-loading="loading" :data="projects" row-key="id" empty-text="暂无项目池记录" @selection-change="onSelectionChange">
      <el-table-column type="selection" width="48" />
      <el-table-column prop="well_no" label="井号" min-width="110" fixed />
      <el-table-column prop="well_type" label="井别" min-width="80" />
      <el-table-column prop="block_name" label="区块" min-width="100" />
      <el-table-column prop="report_unit" label="提报单位" min-width="120" />
      <el-table-column prop="reason_category" label="原因分类" min-width="110" />
      <el-table-column prop="report_batch" label="提报批次" min-width="110" />
      <el-table-column label="资料完整性" min-width="110">
        <template #default="{ row }">
          <el-tag :type="completenessTag(row.completeness_status)">{{ completenessLabel(row.completeness_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="重复井" width="88">
        <template #default="{ row }">
          <el-tag v-if="row.is_duplicate_well" type="warning">是</el-tag>
          <span v-else>否</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" min-width="130">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="附件资料" width="96">
        <template #default="{ row }">{{ attachmentCount(row) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="230" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="openDetail(row)">详情</el-button>
          <el-button v-if="hasPermission('workover_project_pool:update')" text type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button v-if="hasPermission('workover_project_pool:delete')" text type="danger" @click="confirmDelete(row)">作废</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-pagination v-model:current-page="query.page" v-model:page-size="query.page_size" class="pager" layout="total, sizes, prev, pager, next" :total="total" @change="loadProjects" />
  </section>

  <el-dialog v-model="formVisible" :title="dialogTitle" width="960px" class="project-dialog">
    <el-form ref="projectFormRef" :model="projectForm" :rules="projectRules" label-width="108px">
      <div class="form-section-title">基础信息</div>
      <el-row :gutter="16">
        <el-col :span="8"><el-form-item label="井号" prop="well_no"><el-input v-model="projectForm.well_no" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="井名"><el-input v-model="projectForm.well_name" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="层位"><el-input v-model="projectForm.layer" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="提报单位" prop="report_unit"><el-input v-model="projectForm.report_unit" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="属地单位"><el-input v-model="projectForm.territory_unit" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="区块"><el-input v-model="projectForm.block_name" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="井别"><el-input v-model="projectForm.well_type" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="县区"><el-input v-model="projectForm.county" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="发起人"><el-input v-model="projectForm.initiator_name" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="联系电话"><el-input v-model="projectForm.initiator_phone" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="原因分类" prop="reason_category"><el-input v-model="projectForm.reason_category" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="提报批次"><el-input v-model="projectForm.report_batch" /></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="资料完整性"><el-select v-model="projectForm.completeness_status"><el-option label="未完整" value="INCOMPLETE" /><el-option label="完整" value="COMPLETE" /><el-option label="需补充" value="NEEDS_SUPPLEMENT" /></el-select></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="数据来源"><el-select v-model="projectForm.data_source"><el-option label="人工录入" value="manual" /><el-option label="Excel导入" value="excel" /><el-option label="外部同步" value="external" /></el-select></el-form-item></el-col>
        <el-col :span="8"><el-form-item label="优先级"><el-slider v-model="projectForm.production_priority" :max="100" /></el-form-item></el-col>
        <el-col :span="24"><el-form-item label="故障描述"><el-input v-model="projectForm.fault_description" type="textarea" :rows="2" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="上修原因" prop="reason"><el-input v-model="projectForm.reason" /></el-form-item></el-col>
        <el-col :span="12"><el-form-item label="照片要求"><el-input v-model="projectForm.photo_requirement" /></el-form-item></el-col>
        <el-col :span="24"><el-form-item label="补充说明"><el-input v-model="projectForm.rejection_supplement" type="textarea" :rows="2" /></el-form-item></el-col>
      </el-row>

      <div class="measure-head">
        <strong>修井措施</strong>
        <el-button size="small" :icon="Plus" @click="addMeasure">新增措施</el-button>
      </div>
      <div v-for="(measure, index) in projectForm.measures_jsonb.measures" :key="index" class="measure-row">
        <div class="measure-field"><label>措施类型</label><el-input v-model="measure.measure_type" /></div>
        <div class="measure-field"><label>施工工序</label><el-input v-model="measure.process" /></div>
        <div class="measure-field"><label>预计工期(天)</label><el-input-number v-model="measure.duration_days" :min="0" :controls="false" /></div>
        <div class="measure-field"><label>估算费用(万元)</label><el-input-number v-model="measure.estimated_cost" :min="0" :precision="1" :controls="false" /></div>
        <el-button class="measure-delete" :icon="Delete" circle @click="removeMeasure(index)" />
      </div>

      <div class="form-section-title" style="margin-top:16px">附件资料</div>
      <el-form-item label="本地照片">
        <el-upload
          :auto-upload="false"
          :show-file-list="false"
          multiple
          accept=".jpg,.jpeg,.png,.gif,.webp,.bmp,image/jpeg,image/png,image/gif,image/webp,image/bmp"
          :on-change="handlePhotoSelected"
        >
          <el-button :icon="Plus">添加照片</el-button>
        </el-upload>
      </el-form-item>
      <el-form-item label="照片URL">
        <el-input v-model="photoUrlsText" type="textarea" :rows="2" placeholder="多个地址用逗号分隔" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="formVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveProject">保存</el-button>
    </template>
  </el-dialog>

  <el-drawer v-model="detailVisible" title="单井详情" size="48%">
    <template v-if="detailTarget">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="井号">{{ detailTarget.well_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">{{ statusLabel(detailTarget.status) }}</el-descriptions-item>
        <el-descriptions-item label="提报单位">{{ detailTarget.report_unit }}</el-descriptions-item>
        <el-descriptions-item label="资料完整性">{{ completenessLabel(detailTarget.completeness_status) }}</el-descriptions-item>
        <el-descriptions-item label="原因分类">{{ detailTarget.reason_category || '-' }}</el-descriptions-item>
        <el-descriptions-item label="提报批次">{{ detailTarget.report_batch || '-' }}</el-descriptions-item>
        <el-descriptions-item label="数据来源">{{ projectSourceLabel(detailTarget.data_source || 'manual') }}</el-descriptions-item>
        <el-descriptions-item label="重复井">{{ detailTarget.is_duplicate_well ? '是' : '否' }}</el-descriptions-item>
      </el-descriptions>
      <h3>措施内容</h3>
      <el-tag v-for="measure in detailTarget.measures_jsonb.measures || []" :key="measure.measure_type" class="tag-gap">{{ measureTypeLabel(measure.measure_type) }}</el-tag>
      <h3>附件资料</h3>
      <el-empty v-if="!attachmentCount(detailTarget)" description="暂无附件" />
      <div v-else class="photo-preview-grid">
        <div v-for="url in detailTarget.photo_urls || []" :key="url" class="photo-preview-card">
          <el-image :src="url" fit="cover" class="photo-preview-image" :preview-src-list="detailTarget.photo_urls" />
        </div>
      </div>
      <h3>后续闭环</h3>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="运行表状态">审批通过后自动生成修井运行表</el-descriptions-item>
        <el-descriptions-item label="物料状态">由物料模块按井号关联展示</el-descriptions-item>
        <el-descriptions-item label="A5工单状态">由 A5 集成模块回写展示</el-descriptions-item>
      </el-descriptions>
    </template>
  </el-drawer>

  <el-dialog v-model="submitDialogVisible" title="批量提交审批" width="520px">
    <el-input v-model="submitComment" type="textarea" :rows="4" placeholder="提交说明" />
    <template #footer>
      <el-button @click="submitDialogVisible = false">取消</el-button>
      <el-button type="success" :loading="saving" @click="confirmSubmit">提交</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import type { FormInstance, FormRules, UploadFile } from 'element-plus'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Delete, Download, Plus, Promotion, Refresh, Search, Upload } from '@element-plus/icons-vue'
import { createProject, deleteProject, downloadProjectImportTemplate, exportProjects, getProjectAnalytics, importProjects, listProjects, saveBase64File, submitProjects, updateProject } from '../api/workover'
import { emitProjectDataChanged } from '../composables/useProjectSync'
import { readPhotoAttachmentAsDataUrl, validatePhotoAttachment } from '../utils/photoAttachments'
import { statusLabels, statusTagType } from '../utils/status'
import { measureTypeLabel, projectSourceLabel } from '../utils/businessLabels'
import type { ProjectPoolStatus, ProjectQuery, WorkoverProject } from '../types/workover'

const statusOptions = (Object.keys(statusLabels) as ProjectPoolStatus[]).map((value) => ({ label: statusLabels[value], value }))
const query = reactive<ProjectQuery>({ page: 1, page_size: 10, status: '' })
const projects = ref<WorkoverProject[]>([])
const total = ref(0)
const workflowCounts = ref<Record<ProjectPoolStatus, number>>({ DRAFT: 0, PENDING_GEOLOGY_VERIFY: 0, PENDING_PROCESS_VERIFY: 0, APPROVED: 0, REJECTED: 0, DISPATCHED: 0 })
const loading = ref(false)
const saving = ref(false)
const selectedIds = ref<number[]>([])
const formVisible = ref(false)
const detailVisible = ref(false)
const submitDialogVisible = ref(false)
const detailTarget = ref<WorkoverProject | null>(null)
const editingProject = ref<WorkoverProject | null>(null)
const submitComment = ref('')
const projectFormRef = ref<FormInstance>()

function userPermissions(): string[] {
  try { return JSON.parse(localStorage.getItem('permissions') || '[]') } catch { return [] }
}
function hasPermission(perm: string): boolean {
  return userPermissions().includes(perm)
}

const projectForm = reactive<Omit<WorkoverProject, 'id' | 'created_at' | 'updated_at'>>({
  well_no: '', well_name: '', well_type: '', layer: '', fault_description: '', territory_unit: '', block_name: '', county: '',
  report_unit: '', initiator_name: '', initiator_phone: '', production_priority: 60, status: 'DRAFT', reason: '',
  reason_category: '', completeness_status: 'INCOMPLETE', data_source: 'manual', report_batch: '', photo_requirement: '',
  rejection_supplement: '', is_duplicate_well: false, related_project_ids: [], measures_jsonb: { measures: [] }, photo_urls: [], attachments: [], remark: ''
})
const projectRules: FormRules = {
  well_no: [{ required: true, message: '请输入井号', trigger: 'blur' }],
  report_unit: [{ required: true, message: '请输入提报单位', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入上修原因', trigger: 'blur' }],
  reason_category: [{ required: true, message: '请输入原因分类', trigger: 'blur' }]
}
const dialogTitle = computed(() => editingProject.value ? '编辑项目池提报' : '新增上修提报')
const photoUrlsText = computed<string>({
  get() { return (projectForm.photo_urls || []).join(', ') },
  set(val: string) { projectForm.photo_urls = val ? val.split(',').map((s) => s.trim()).filter(Boolean) : [] }
})
const totalProjectCount = computed(() => Object.values(workflowCounts.value).reduce((sum, value) => sum + value, 0))
const supplementCount = computed(() => projects.value.filter((item) => item.completeness_status === 'NEEDS_SUPPLEMENT').length)
const duplicateCount = computed(() => projects.value.filter((item) => item.is_duplicate_well).length)

function countStatus(status: ProjectPoolStatus) { return workflowCounts.value[status] || 0 }
function statusLabel(status: ProjectPoolStatus) { return statusLabels[status] }
function completenessLabel(status?: string) {
  return status === 'COMPLETE' ? '完整' : status === 'NEEDS_SUPPLEMENT' ? '需补充' : '未完整'
}
function completenessTag(status?: string) {
  return status === 'COMPLETE' ? 'success' : status === 'NEEDS_SUPPLEMENT' ? 'warning' : 'info'
}
function attachmentCount(row: WorkoverProject) {
  return (row.attachments?.length || 0) + (row.photo_urls?.length || 0)
}
async function loadProjects() {
  loading.value = true
  try {
    // Direct fetch to bypass any Axios/compactQuery issues
    const token = localStorage.getItem('access_token')
    const resp = await fetch('/api/v1/workover-project-pools/?page=1&page_size=20', {
      headers: { 'Authorization': 'Bearer ' + (token || '') }
    })
    const json = await resp.json()
    if (json.code === 20000 && json.data) {
      projects.value = json.data.items || []
      total.value = json.data.total || 0
    } else {
      ElMessage.error(json.msg || '接口返回异常')
      projects.value = []
      total.value = 0
    }
    selectedIds.value = []
  } catch (error: any) {
    ElMessage.error(error?.message || '加载项目列表失败')
    projects.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}
async function loadWorkflowCounts() {
  const summary = await getProjectAnalytics({})
  const nextCounts: Record<ProjectPoolStatus, number> = { DRAFT: 0, PENDING_GEOLOGY_VERIFY: 0, PENDING_PROCESS_VERIFY: 0, APPROVED: 0, REJECTED: 0, DISPATCHED: 0 }
  summary.status_counts.forEach((item) => { nextCounts[item.status] = item.count })
  workflowCounts.value = nextCounts
}
function resetQuery() {
  Object.assign(query, { page: 1, page_size: query.page_size, status: '', well_no: '', block_name: '', measure_type: '' })
  loadProjects()
}
function resetForm() {
  Object.assign(projectForm, {
    well_no: '', well_name: '', well_type: '', layer: '', fault_description: '', territory_unit: '', block_name: '', county: '',
    report_unit: '', initiator_name: '', initiator_phone: '', production_priority: 60, status: 'DRAFT', reason: '',
    reason_category: '', completeness_status: 'INCOMPLETE', data_source: 'manual', report_batch: '', photo_requirement: '',
    rejection_supplement: '', is_duplicate_well: false, related_project_ids: [], measures_jsonb: { measures: [{ measure_type: '', process: '', construction_params: {}, duration_days: 0, estimated_cost: 0 }] }, photo_urls: [], attachments: [], remark: ''
  })
}
function openCreate() { editingProject.value = null; resetForm(); formVisible.value = true }
function openEdit(row: WorkoverProject) { editingProject.value = row; Object.assign(projectForm, JSON.parse(JSON.stringify(row))); formVisible.value = true }
function openDetail(row: WorkoverProject) { detailTarget.value = row; detailVisible.value = true }
function addMeasure() { projectForm.measures_jsonb.measures = projectForm.measures_jsonb.measures || []; projectForm.measures_jsonb.measures.push({ measure_type: '', process: '', construction_params: {}, duration_days: 0, estimated_cost: 0 }) }
function removeMeasure(index: number) { projectForm.measures_jsonb.measures?.splice(index, 1) }
function onSelectionChange(rows: WorkoverProject[]) { selectedIds.value = rows.map((row) => row.id) }
async function handlePhotoSelected(uploadFile: UploadFile) {
  const raw = uploadFile.raw
  if (!raw) return
  const validationMessage = validatePhotoAttachment(raw)
  if (validationMessage) {
    ElMessage.warning(validationMessage)
    return
  }
  const dataUrl = await readPhotoAttachmentAsDataUrl(raw)
  projectForm.photo_urls = [...(projectForm.photo_urls || []), dataUrl]
  projectForm.attachments = [
    ...(projectForm.attachments || []),
    {
      name: raw.name,
      url: dataUrl,
      content_type: raw.type,
      size: raw.size,
      category: 'wellsite',
      uploaded_by: '当前用户',
      uploaded_at: new Date().toISOString()
    }
  ]
}
async function saveProject() {
  try { await projectFormRef.value?.validate() } catch { return }
  if (!(projectForm.measures_jsonb.measures || []).some((measure) => measure.measure_type)) {
    ElMessage.warning('请至少填写一条措施类型')
    return
  }
  saving.value = true
  try {
    if (editingProject.value) await updateProject(editingProject.value.id, projectForm)
    else await createProject(projectForm)
    ElMessage.success('保存成功')
    formVisible.value = false
    emitProjectDataChanged()
    await Promise.all([loadWorkflowCounts(), loadProjects()])
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.message || '保存失败')
  } finally {
    saving.value = false
  }
}
async function confirmSubmit() {
  saving.value = true
  try {
    await submitProjects(selectedIds.value, submitComment.value)
    ElNotification.success({ title: '提交成功', message: '已提交至审核节点' })
    submitDialogVisible.value = false
    emitProjectDataChanged()
    await Promise.all([loadWorkflowCounts(), loadProjects()])
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.message || '提交失败')
  } finally {
    saving.value = false
  }
}
async function handleImportSelected(uploadFile: UploadFile) {
  if (!uploadFile.raw) return
  try {
    const result = await importProjects(uploadFile.raw)
    ElMessage.success(`导入成功：${result.imported_count} 条`)
    await Promise.all([loadWorkflowCounts(), loadProjects()])
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.message || '导入失败')
  }
}
async function downloadTemplate() { saveBase64File(await downloadProjectImportTemplate()) }
async function downloadExport() { saveBase64File(await exportProjects()) }
async function confirmDelete(row: WorkoverProject) {
  try { await ElMessageBox.confirm(`确认作废项目 ${row.well_no} 吗？`, '作废项目', { type: 'warning' }) } catch { return }
  await deleteProject(row.id)
  ElMessage.success('已作废')
  await Promise.all([loadWorkflowCounts(), loadProjects()])
}
onMounted(() => { loadProjects(); loadWorkflowCounts() })
</script>
