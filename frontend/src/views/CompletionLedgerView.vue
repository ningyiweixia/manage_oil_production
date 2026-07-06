<template>
  <section class="toolbar">
    <el-form :model="query" inline>
      <el-form-item label="井号">
        <el-input v-model="query.well_no" clearable placeholder="输入井号" />
      </el-form-item>
      <el-form-item label="措施类型">
        <el-input v-model="query.measure_type" clearable placeholder="输入措施类型" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadAll">查询</el-button>
        <el-button :icon="Plus" @click="openCreate">新增记录</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="stats-bar">
    <div class="stats-card">
      <span class="stats-label">完井记录</span>
      <strong class="stats-value">{{ analytics?.total || 0 }}</strong>
    </div>
    <div v-for="item in analytics?.by_measure_type || []" :key="item.measure_type" class="stats-card">
      <span class="stats-label">{{ item.measure_type }}</span>
      <strong class="stats-value primary">{{ item.count }}</strong>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>完井分类台账</h2>
        <p>沉淀修前、修后关键数据，按措施类型形成分类台账。</p>
      </div>
    </div>
    <el-table v-loading="loading" :data="rows" row-key="id">
      <el-table-column prop="well_no" label="井号" width="120" />
      <el-table-column prop="measure_type" label="措施类型" min-width="130" />
      <el-table-column prop="completion_date" label="完井日期" width="120" />
      <el-table-column prop="team_name" label="施工队伍" min-width="140" />
      <el-table-column label="修前数据" min-width="180">
        <template #default="{ row }">{{ dataSummary(row.pre_repair_data) }}</template>
      </el-table-column>
      <el-table-column label="修后数据" min-width="180">
        <template #default="{ row }">{{ dataSummary(row.post_repair_data) }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="remove(row)">删除</el-button>
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

  <el-dialog v-model="visible" :title="editing ? '编辑完井记录' : '新增完井记录'" width="680px" @closed="resetForm">
    <el-form :model="form" label-width="108px">
      <el-form-item label="井号"><el-input v-model="form.well_no" /></el-form-item>
      <el-form-item label="运行表ID"><el-input-number v-model="form.operation_sheet_id" :min="1" clearable /></el-form-item>
      <el-form-item label="措施类型"><el-input v-model="form.measure_type" /></el-form-item>
      <el-form-item label="完井日期"><el-date-picker v-model="form.completion_date" value-format="YYYY-MM-DD" /></el-form-item>
      <el-form-item label="施工队伍"><el-input v-model="form.team_name" /></el-form-item>
      <el-form-item label="修前产量"><el-input v-model="form.production_before" /></el-form-item>
      <el-form-item label="修后产量"><el-input v-model="form.production_after" /></el-form-item>
      <el-form-item label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import {
  createWellCompletion,
  deleteWellCompletion,
  getCompletionAnalytics,
  listWellCompletions,
  updateWellCompletion,
  type CompletionAnalytics,
  type WellCompletionRecord
} from '../api/completion'

const loading = ref(false)
const saving = ref(false)
const visible = ref(false)
const total = ref(0)
const rows = ref<WellCompletionRecord[]>([])
const analytics = ref<CompletionAnalytics | null>(null)
const editing = ref<WellCompletionRecord | null>(null)
const query = reactive({ page: 1, page_size: 20, well_no: '', measure_type: '' })
const form = reactive({
  well_no: '',
  operation_sheet_id: undefined as number | undefined,
  measure_type: '',
  completion_date: '',
  team_name: '',
  production_before: '',
  production_after: '',
  remark: ''
})

function dataSummary(value: Record<string, unknown>) {
  const entries = Object.entries(value || {}).filter(([, item]) => item !== undefined && item !== null && item !== '')
  if (!entries.length) return '-'
  return entries.map(([key, item]) => `${key}: ${item}`).join('；')
}

function payload() {
  return {
    well_no: form.well_no,
    operation_sheet_id: form.operation_sheet_id || null,
    measure_type: form.measure_type,
    completion_date: form.completion_date || undefined,
    team_name: form.team_name,
    pre_repair_data: { production_before: form.production_before },
    post_repair_data: { production_after: form.production_after },
    remark: form.remark
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [page, summary] = await Promise.all([
      listWellCompletions(query),
      getCompletionAnalytics()
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

function openEdit(row: WellCompletionRecord) {
  editing.value = row
  Object.assign(form, {
    well_no: row.well_no,
    operation_sheet_id: row.operation_sheet_id || undefined,
    measure_type: row.measure_type,
    completion_date: row.completion_date || '',
    team_name: row.team_name || '',
    production_before: String(row.pre_repair_data?.production_before || ''),
    production_after: String(row.post_repair_data?.production_after || ''),
    remark: row.remark || ''
  })
  visible.value = true
}

function resetForm() {
  Object.assign(form, {
    well_no: '',
    operation_sheet_id: undefined,
    measure_type: '',
    completion_date: '',
    team_name: '',
    production_before: '',
    production_after: '',
    remark: ''
  })
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await updateWellCompletion(editing.value.id, payload())
      ElMessage.success('完井记录已更新')
    } else {
      await createWellCompletion(payload())
      ElMessage.success('完井记录已创建')
    }
    visible.value = false
    await loadAll()
  } finally {
    saving.value = false
  }
}

async function remove(row: WellCompletionRecord) {
  await ElMessageBox.confirm(`确认删除井号「${row.well_no}」的完井记录吗？`, '删除完井记录', { type: 'warning' })
  await deleteWellCompletion(row.id)
  ElMessage.success('已删除')
  await loadAll()
}

onMounted(loadAll)
</script>
