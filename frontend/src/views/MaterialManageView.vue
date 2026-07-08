<template>
  <section class="toolbar">
    <el-form :model="query" inline>
      <el-form-item label="井号">
        <el-input v-model="query.well_no" clearable placeholder="输入井号" />
      </el-form-item>
      <el-form-item label="物料">
        <el-input v-model="query.material_name" clearable placeholder="输入物料名称" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="query.status" clearable placeholder="全部状态" style="width: 150px">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="异常">
        <el-select v-model="query.has_exception" clearable placeholder="全部" style="width: 120px">
          <el-option label="有异常" :value="true" />
          <el-option label="无异常" :value="false" />
        </el-select>
      </el-form-item>
      <el-form-item label="来源">
        <el-input v-model="query.source_platform" clearable placeholder="internal" style="width: 130px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadAll">查询</el-button>
        <el-button v-if="canCreate" :icon="Plus" @click="openCreate">新增需求</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="stats-bar">
    <div class="stats-card">
      <span class="stats-label">物料需求</span>
      <strong class="stats-value">{{ analytics?.total || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">待处理</span>
      <strong class="stats-value warn">{{ analytics?.pending || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">已计划</span>
      <strong class="stats-value primary">{{ analytics?.planned || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">已出库</span>
      <strong class="stats-value primary">{{ analytics?.delivered || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">已到场</span>
      <strong class="stats-value success">{{ analytics?.arrived || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">异常情况</span>
      <strong class="stats-value danger">{{ analytics?.exception_count || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">使用率</span>
      <strong class="stats-value success">{{ analytics?.usage_rate || 0 }}%</strong>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>{{ isDeliveryView ? '物料配送跟踪' : '物料需求台账' }}</h2>
        <p>围绕修井任务记录物料需求、计划、出库、配送、到场、使用和异常情况。</p>
      </div>
    </div>

    <el-table v-loading="loading" :data="rows" row-key="id">
      <el-table-column prop="well_no" label="井号" width="120" />
      <el-table-column prop="operation_sheet_id" label="运行表ID" width="100" />
      <el-table-column prop="material_name" label="物料名称" min-width="150" />
      <el-table-column prop="specification" label="规格型号" min-width="140" show-overflow-tooltip />
      <el-table-column label="需求数量" width="110">
        <template #default="{ row }">{{ row.quantity }} {{ row.unit }}</template>
      </el-table-column>
      <el-table-column label="计划数量" width="100">
        <template #default="{ row }">{{ row.planned_quantity }}</template>
      </el-table-column>
      <el-table-column label="出库数量" width="100">
        <template #default="{ row }">{{ row.delivered_quantity }}</template>
      </el-table-column>
      <el-table-column label="到场数量" width="100">
        <template #default="{ row }">{{ row.arrived_quantity }}</template>
      </el-table-column>
      <el-table-column label="使用数量" width="100">
        <template #default="{ row }">{{ row.used_quantity }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="预计到场" width="160">
        <template #default="{ row }">{{ formatDate(row.expected_arrival_at) }}</template>
      </el-table-column>
      <el-table-column label="异常情况" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <el-tag v-if="row.exception_reason" type="danger">{{ row.exception_reason }}</el-tag>
          <span v-else class="muted">无</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" fixed="right" width="300">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button v-if="canUpdate && row.status === 'PENDING'" text type="primary" @click="advance(row, 'APPROVED')">审核</el-button>
            <el-button v-if="canUpdate && row.status === 'APPROVED'" text type="primary" @click="advance(row, 'PLANNED')">计划</el-button>
            <el-button v-if="canUpdate && row.status === 'PLANNED'" text type="primary" @click="advance(row, 'DELIVERED')">出库</el-button>
            <el-button v-if="canUpdate && row.status === 'DELIVERED'" text type="success" @click="advance(row, 'ARRIVED')">到场</el-button>
            <el-button v-if="canUpdate && row.status === 'ARRIVED'" text type="success" @click="advance(row, 'USED')">使用</el-button>
            <el-button v-if="canUpdate" text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="canUpdate && canCancel(row.status)" text type="warning" @click="advance(row, 'CANCELED')">取消</el-button>
            <el-button v-if="canDelete(row.status)" text type="danger" @click="remove(row)">删除</el-button>
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
      @change="loadAll"
    />
  </section>

  <el-dialog v-model="visible" :title="editing ? '编辑物料需求' : '新增物料需求'" width="760px" @closed="resetForm">
    <el-form :model="form" label-width="110px">
      <div class="form-grid">
        <el-form-item label="井号"><el-input v-model="form.well_no" /></el-form-item>
        <el-form-item label="运行表ID"><el-input-number v-model="form.operation_sheet_id" :min="1" clearable /></el-form-item>
        <el-form-item label="物料名称"><el-input v-model="form.material_name" /></el-form-item>
        <el-form-item label="规格型号"><el-input v-model="form.specification" /></el-form-item>
        <el-form-item label="需求数量">
          <el-input-number v-model="form.quantity" :min="0.01" :precision="2" />
          <el-input v-model="form.unit" class="unit-input" />
        </el-form-item>
        <el-form-item label="需求类型"><el-segmented v-model="form.requirement_type" :options="typeOptions" /></el-form-item>
        <el-form-item label="计划号"><el-input v-model="form.plan_no" /></el-form-item>
        <el-form-item label="仓库"><el-input v-model="form.warehouse" /></el-form-item>
        <el-form-item label="配送队伍"><el-input v-model="form.supplier_or_team" /></el-form-item>
        <el-form-item label="计划数量"><el-input-number v-model="form.planned_quantity" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="出库数量"><el-input-number v-model="form.delivered_quantity" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="到场数量"><el-input-number v-model="form.arrived_quantity" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="使用数量"><el-input-number v-model="form.used_quantity" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="预计到场">
          <el-date-picker v-model="form.expected_arrival_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="联系人"><el-input v-model="form.delivery_contact" /></el-form-item>
        <el-form-item label="联系电话"><el-input v-model="form.delivery_phone" /></el-form-item>
        <el-form-item label="来源平台"><el-input v-model="form.source_platform" /></el-form-item>
        <el-form-item label="外部ID"><el-input v-model="form.external_material_id" /></el-form-item>
      </div>
      <el-form-item v-if="editing" label="状态">
        <el-select v-model="form.status" style="width: 180px">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="异常情况"><el-input v-model="form.exception_reason" type="textarea" :rows="2" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="2" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import {
  createMaterialRequirement,
  deleteMaterialRequirement,
  getMaterialAnalytics,
  listMaterialRequirements,
  updateMaterialRequirement,
  type MaterialAnalytics,
  type MaterialRequirement,
  type MaterialRequirementStatus,
  type MaterialRequirementType
} from '../api/material'

const route = useRoute()
const isDeliveryView = computed(() => route.path === '/material/delivery')
const permissions = computed<string[]>(() => {
  try {
    return JSON.parse(localStorage.getItem('permissions') || '[]')
  } catch {
    return []
  }
})
const canCreate = computed(() => permissions.value.includes('material:create'))
const canUpdate = computed(() => permissions.value.includes('material:update'))

const loading = ref(false)
const saving = ref(false)
const visible = ref(false)
const total = ref(0)
const rows = ref<MaterialRequirement[]>([])
const analytics = ref<MaterialAnalytics | null>(null)
const editing = ref<MaterialRequirement | null>(null)
const query = reactive<{
  page: number
  page_size: number
  well_no: string
  material_name: string
  status: MaterialRequirementStatus | ''
  has_exception: boolean | ''
  source_platform: string
}>({
  page: 1,
  page_size: 20,
  well_no: '',
  material_name: '',
  status: '',
  has_exception: '',
  source_platform: ''
})
const form = reactive({
  well_no: '',
  operation_sheet_id: undefined as number | undefined,
  material_name: '',
  specification: '',
  quantity: 1,
  unit: '件',
  plan_no: '',
  warehouse: '',
  supplier_or_team: '',
  planned_quantity: 0,
  delivered_quantity: 0,
  arrived_quantity: 0,
  used_quantity: 0,
  delivery_contact: '',
  delivery_phone: '',
  expected_arrival_at: '',
  exception_reason: '',
  source_platform: 'internal',
  external_material_id: '',
  requirement_type: 'NORMAL' as MaterialRequirementType,
  status: 'PENDING' as MaterialRequirementStatus,
  remark: ''
})
const statusOptions: Array<{ label: string; value: MaterialRequirementStatus }> = [
  { label: '待处理', value: 'PENDING' },
  { label: '已审核', value: 'APPROVED' },
  { label: '已计划', value: 'PLANNED' },
  { label: '已出库', value: 'DELIVERED' },
  { label: '已到场', value: 'ARRIVED' },
  { label: '已使用', value: 'USED' },
  { label: '已取消', value: 'CANCELED' }
]
const typeOptions = [
  { label: '正常需求', value: 'NORMAL' },
  { label: '紧急需求', value: 'EMERGENCY' }
]

function statusLabel(status: MaterialRequirementStatus) {
  return statusOptions.find((item) => item.value === status)?.label || status
}

function statusTag(status: MaterialRequirementStatus) {
  if (status === 'USED' || status === 'ARRIVED') return 'success'
  if (status === 'DELIVERED' || status === 'PLANNED') return 'primary'
  if (status === 'CANCELED') return 'info'
  return 'warning'
}

function canCancel(status: MaterialRequirementStatus) {
  return !['USED', 'CANCELED'].includes(status)
}

function canDelete(status: MaterialRequirementStatus) {
  return canUpdate.value && (status === 'PENDING' || status === 'CANCELED')
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 16)
}

function applyRouteDefaults() {
  if (isDeliveryView.value && !query.status) {
    query.status = 'DELIVERED'
  }
}

async function loadAll() {
  loading.value = true
  try {
    applyRouteDefaults()
    const [page, summary] = await Promise.all([
      listMaterialRequirements(query),
      getMaterialAnalytics(query.well_no || undefined)
    ])
    rows.value = page.items
    total.value = page.total
    analytics.value = summary
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  visible.value = true
}

function openEdit(row: MaterialRequirement) {
  editing.value = row
  Object.assign(form, {
    well_no: row.well_no,
    operation_sheet_id: row.operation_sheet_id || undefined,
    material_name: row.material_name,
    specification: row.specification || '',
    quantity: row.quantity,
    unit: row.unit,
    plan_no: row.plan_no || '',
    warehouse: row.warehouse || '',
    supplier_or_team: row.supplier_or_team || '',
    planned_quantity: row.planned_quantity || 0,
    delivered_quantity: row.delivered_quantity || 0,
    arrived_quantity: row.arrived_quantity || 0,
    used_quantity: row.used_quantity || 0,
    delivery_contact: row.delivery_contact || '',
    delivery_phone: row.delivery_phone || '',
    expected_arrival_at: row.expected_arrival_at || '',
    exception_reason: row.exception_reason || '',
    source_platform: row.source_platform || 'internal',
    external_material_id: row.external_material_id || '',
    requirement_type: row.requirement_type,
    status: row.status,
    remark: row.remark || ''
  })
  visible.value = true
}

function resetForm() {
  Object.assign(form, {
    well_no: '',
    operation_sheet_id: undefined,
    material_name: '',
    specification: '',
    quantity: 1,
    unit: '件',
    plan_no: '',
    warehouse: '',
    supplier_or_team: '',
    planned_quantity: 0,
    delivered_quantity: 0,
    arrived_quantity: 0,
    used_quantity: 0,
    delivery_contact: '',
    delivery_phone: '',
    expected_arrival_at: '',
    exception_reason: '',
    source_platform: 'internal',
    external_material_id: '',
    requirement_type: 'NORMAL',
    status: 'PENDING',
    remark: ''
  })
}

function payloadFromForm() {
  return {
    ...form,
    operation_sheet_id: form.operation_sheet_id || null,
    plan_no: form.plan_no || null,
    warehouse: form.warehouse || null,
    supplier_or_team: form.supplier_or_team || null,
    delivery_contact: form.delivery_contact || null,
    delivery_phone: form.delivery_phone || null,
    expected_arrival_at: form.expected_arrival_at || null,
    exception_reason: form.exception_reason || null,
    external_material_id: form.external_material_id || null
  }
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await updateMaterialRequirement(editing.value.id, payloadFromForm())
      ElMessage.success('物料需求已更新')
    } else {
      await createMaterialRequirement(payloadFromForm())
      ElMessage.success('物料需求已创建')
    }
    visible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function advance(row: MaterialRequirement, status: MaterialRequirementStatus) {
  const label = statusLabel(status)
  await ElMessageBox.confirm(`确认将「${row.material_name}」推进为${label}吗？`, label, { type: 'warning' })
  await updateMaterialRequirement(row.id, { status })
  ElMessage.success(`已更新为${label}`)
  await loadAll()
}

async function remove(row: MaterialRequirement) {
  await ElMessageBox.confirm(`确认删除「${row.material_name}」吗？`, '删除物料需求', { type: 'warning' })
  await deleteMaterialRequirement(row.id)
  ElMessage.success('已删除')
  await loadAll()
}

watch(() => route.path, () => {
  query.status = ''
  query.page = 1
  loadAll()
})

onMounted(loadAll)
</script>

<style scoped>
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 16px;
}

.unit-input {
  width: 80px;
  margin-left: 8px;
}

.muted {
  color: var(--el-text-color-secondary);
}

@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
