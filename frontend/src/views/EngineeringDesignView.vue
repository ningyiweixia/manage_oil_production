<template>
  <section class="toolbar">
    <el-form :model="query" inline>
      <el-form-item label="井号">
        <el-input v-model="query.well_no" clearable placeholder="输入井号" />
      </el-form-item>
      <el-form-item label="项目ID">
        <el-input-number v-model="query.project_id" :min="1" clearable />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadDesigns">查询</el-button>
        <el-button :icon="DocumentAdd" @click="generateVisible = true">生成设计</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>工程设计文档</h2>
        <p>生成前执行规则校验，产出 Word/Excel 后归档到 MinIO。</p>
      </div>
    </div>
    <el-table v-loading="loading" :data="designs" row-key="id">
      <el-table-column prop="well_no" label="井号" width="120" />
      <el-table-column prop="project_id" label="项目ID" width="90" />
      <el-table-column prop="version" label="版本" width="90" />
      <el-table-column prop="minio_bucket" label="存储桶" min-width="160" />
      <el-table-column prop="minio_object_key" label="对象路径" min-width="260" show-overflow-tooltip />
      <el-table-column prop="created_at" label="生成时间" min-width="180" />
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button text type="primary" @click="download(row.id)">下载</el-button>
            <el-button text type="danger" @click="remove(row.id)">删除</el-button>
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
      @change="loadDesigns"
    />
  </section>

  <el-dialog v-model="generateVisible" title="生成工程设计" width="560px">
    <el-form :model="generateForm" label-width="104px">
      <el-form-item label="项目ID"><el-input-number v-model="generateForm.project_id" :min="1" /></el-form-item>
      <el-form-item label="井号"><el-input v-model="generateForm.well_no" /></el-form-item>
      <el-form-item label="模板类型">
        <el-segmented v-model="generateForm.template_type" :options="templateOptions" />
      </el-form-item>
      <el-alert
        v-if="ruleResult"
        :type="ruleResult.passed ? 'success' : 'error'"
        :closable="false"
        show-icon
        :title="ruleResult.passed ? '规则校验通过' : '规则校验未通过'"
      >
        <template #default>
          <div v-if="ruleResult.errors.length">{{ ruleResult.errors.join('；') }}</div>
          <div v-if="ruleResult.warnings.length">{{ ruleResult.warnings.join('；') }}</div>
        </template>
      </el-alert>
    </el-form>
    <template #footer>
      <el-button @click="checkRules">规则校验</el-button>
      <el-button @click="generateVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="confirmGenerate">生成</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DocumentAdd, Search } from '@element-plus/icons-vue'
import {
  checkDesignRules,
  deleteDesign,
  generateDesign,
  getDesignDownloadUrl,
  listDesigns,
  type EngineeringDesign,
  type RuleCheckResult
} from '../api/engineering'

const loading = ref(false)
const saving = ref(false)
const total = ref(0)
const designs = ref<EngineeringDesign[]>([])
const generateVisible = ref(false)
const ruleResult = ref<RuleCheckResult | null>(null)
const query = reactive<{ page: number; page_size: number; well_no?: string; project_id?: number }>({ page: 1, page_size: 20 })
const generateForm = reactive<{ project_id: number; well_no: string; template_type: 'word' | 'excel' }>({
  project_id: 1,
  well_no: '',
  template_type: 'word'
})
const templateOptions = [
  { label: 'Word', value: 'word' },
  { label: 'Excel', value: 'excel' }
]

async function loadDesigns() {
  loading.value = true
  try {
    const page = await listDesigns(query)
    designs.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

async function checkRules() {
  ruleResult.value = await checkDesignRules(generateForm.project_id)
}

async function confirmGenerate() {
  saving.value = true
  try {
    const result = await generateDesign(generateForm)
    ruleResult.value = result.rule_check
    ElMessage.success(`已生成 ${result.design.well_no} ${result.design.version}`)
    generateVisible.value = false
    await loadDesigns()
  } finally {
    saving.value = false
  }
}

async function download(id: number) {
  const result = await getDesignDownloadUrl(id)
  window.open(result.download_url, '_blank')
}

async function remove(id: number) {
  await ElMessageBox.confirm('确认删除该设计文档记录吗？', '删除确认', { type: 'warning' })
  await deleteDesign(id)
  ElMessage.success('已删除')
  await loadDesigns()
}

onMounted(loadDesigns)
</script>
