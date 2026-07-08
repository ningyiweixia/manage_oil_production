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
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadAll">查询</el-button>
        <el-button :icon="Plus" @click="openCreate">新增需求</el-button>
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
      <span class="stats-label">已出库</span>
      <strong class="stats-value primary">{{ analytics?.delivered || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">已到场</span>
      <strong class="stats-value success">{{ analytics?.arrived || 0 }}</strong>
    </div>
    <div class="stats-card">
      <span class="stats-label">紧急需求</span>
      <strong class="stats-value danger">{{ analytics?.emergency_count || 0 }}</strong>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>{{ isDeliveryView ? '物料配送与状态跟踪' : '物料需求台账' }}</h2>
        <p>按井号、物料、需求类型和配送状态沉淀物料保障记录。</p>
      </div>
    </div>
    <el-table v-loading="loading" :data="rows" row-key="id">
      <el-table-column prop="well_no" label="井号" width="120" />
      <el-table-column prop="material_name" label="物料名称" min-width="150" />
      <el-table-column prop="specification" label="规格型号" min-width="140" show-overflow-tooltip />
      <el-table-column label="数量" width="110">
        <template #default="{ row }">{{ row.quantity }} {{ row.unit }}</template>
      </el-table-column>
      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.requirement_type === 'EMERGENCY' ? 'danger' : 'info'">{{ typeLabel(row.requirement_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="170">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" :disabled="!canDelete(row.status)" @click="remove(row)">删除</el-button>
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

  <el-dialog v-model="visible" :title="editing ? '编辑物料需求' : '新增物料需求'" width="640px" @closed="resetForm">
    <el-form :model="form" label-width="108px">
      <el-form-item label="井号"><el-input v-model="form.well_no" /></el-form-item>
      <el-form-item label="运行表ID"><el-input-number v-model="form.operation_sheet_id" :min="1" clearable /></el-form-item>
      <el-form-item label="物料名称"><el-input v-model="form.material_name" /></el-form-item>
      <el-form-item label="规格型号"><el-input v-model="form.specification" /></el-form-item>
      <el-form-item label="数量">
        <el-input-number v-model="form.quantity" :min="0.01" :precision="2" />
        <el-input v-model="form.unit" class="unit-input" />
      </el-form-item>
      <el-form-item label="需求类型">
        <el-segmented v-model="form.requirement_type" :options="typeOptions" />
      </el-form-item>
      <el-form-item v-if="editing" label="状态">
        <el-select v-model="form.status" style="width: 180px">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item>
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
const loading = ref(false)
const saving = ref(false)
const visible = ref(false)
const total = ref(0)
const rows = ref<MaterialRequirement[]>([])
const analytics = ref<MaterialAnalytics | null>(null)
const editing = ref<MaterialRequirement | null>(null)
const query = reactive<{ page: number; page_size: number; well_no: string; material_name: string; status: MaterialRequirementStatus | '' }>({
  page: 1,
  page_size: 20,
  well_no: '',
  material_name: '',
  status: ''
})
const form = reactive({
  well_no: '',
  operation_sheet_id: undefined as number | undefined,
  material_name: '',
  specification: '',
  quantity: 1,
  unit: '件',
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

function typeLabel(type: MaterialRequirementType) {
  return type === 'EMERGENCY' ? '紧急' : '正常'
}

function statusTag(status: MaterialRequirementStatus) {
  if (status === 'USED' || status === 'ARRIVED') return 'success'
  if (status === 'DELIVERED' || status === 'PLANNED') return 'primary'
  if (status === 'CANCELED') return 'info'
  return 'warning'
}

function canDelete(status: MaterialRequirementStatus) {
  return status === 'PENDING' || status === 'CANCELED'
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
    requirement_type: 'NORMAL',
    status: 'PENDING',
    remark: ''
  })
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await updateMaterialRequirement(editing.value.id, form)
      ElMessage.success('物料需求已更新')
    } else {
      await createMaterialRequirement(form)
      ElMessage.success('物料需求已创建')
    }
    visible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
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
.unit-input {
  width: 80px;
  margin-left: 8px;
}
</style>
