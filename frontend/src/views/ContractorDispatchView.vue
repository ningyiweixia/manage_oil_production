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
        <el-button type="primary" :icon="Search" @click="loadContractors">查询</el-button>
        <el-button :icon="Plus" @click="openContractor">运力报备</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="source-summary">
    <div>
      <strong>承包商系统对接</strong>
      <span>本页保留外部承包商队伍资源入口，派工执行与运行表进度由厂内运行模块统一管理。</span>
    </div>
    <el-tag effect="plain">外部系统接口</el-tag>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>承包商运力</h2>
        <p>维护外部承包商系统同步前的队伍状态和施工能力标签。</p>
      </div>
    </div>
    <el-table v-loading="loading" :data="contractors" row-key="id" empty-text="暂无承包商运力">
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
      <el-form-item label="大修资质"><el-switch v-model="majorRepair" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="contractorVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="saveContractor">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import {
  createContractor,
  listContractors,
  type ContractorCapacity,
  type ContractorQuery,
  type ContractorStatus
} from '../api/contractor'

const contractorStatusText: Record<ContractorStatus, string> = { AVAILABLE: '可用', BUSY: '忙碌', OFFLINE: '离线' }
const loading = ref(false)
const saving = ref(false)
const contractors = ref<ContractorCapacity[]>([])
const contractorQuery = reactive<ContractorQuery>({ page: 1, page_size: 50, status: '' })
const contractorVisible = ref(false)
const majorRepair = ref(false)
const contractorForm = reactive({
  contractor_name: '',
  team_name: '',
  report_date: new Date().toISOString().slice(0, 10),
  available_count: 1,
  status: 'AVAILABLE' as ContractorStatus,
  capability_tags: {}
})

function contractorTag(status: ContractorStatus) {
  return status === 'AVAILABLE' ? 'success' : status === 'BUSY' ? 'warning' : 'info'
}

function contractorStatusLabel(status: ContractorStatus) {
  return contractorStatusText[status] || status
}

async function loadContractors() {
  loading.value = true
  try {
    const result = await listContractors(contractorQuery)
    contractors.value = result.items
  } finally {
    loading.value = false
  }
}

function openContractor() {
  contractorVisible.value = true
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
    await loadContractors()
  } finally {
    saving.value = false
  }
}

onMounted(loadContractors)
</script>
