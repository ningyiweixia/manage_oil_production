<template>
  <section class="toolbar">
    <el-form :model="query" inline>
      <el-form-item label="字典类型">
        <el-input v-model="query.dict_type" clearable placeholder="measure_type" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadItems">查询</el-button>
        <el-button :icon="Plus" @click="openCreate">新增字典项</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>数据字典</h2>
        <p>维护井号资源、修井措施类型、工序标准等动态选项。</p>
      </div>
    </div>
    <el-table v-loading="loading" :data="filteredItems" row-key="id">
      <el-table-column prop="dict_type" label="类型" min-width="160" />
      <el-table-column prop="item_label" label="显示名称" min-width="180" />
      <el-table-column prop="item_value" label="取值" min-width="180" />
      <el-table-column label="启用" width="90">
        <template #default="{ row }">
          <el-switch :model-value="row.is_active" @change="(value: string | number | boolean) => changeActive(row.id, Boolean(value))" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button text type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
  </section>

  <el-dialog v-model="visible" :title="editing ? '编辑字典项' : '新增字典项'" width="520px">
    <el-form :model="form" label-width="100px">
      <el-form-item label="类型"><el-input v-model="form.dict_type" /></el-form-item>
      <el-form-item label="显示名称"><el-input v-model="form.item_label" /></el-form-item>
      <el-form-item label="取值"><el-input v-model="form.item_value" /></el-form-item>
      <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Search } from '@element-plus/icons-vue'
import {
  createDictionaryItem,
  listAllDictionaryItems,
  setDictionaryActive,
  updateDictionaryItem,
  type DictionaryItem
} from '../api/dictionary'

const loading = ref(false)
const saving = ref(false)
const visible = ref(false)
const editing = ref<DictionaryItem | null>(null)
const items = ref<DictionaryItem[]>([])
const query = reactive({ dict_type: '' })
const form = reactive({ dict_type: '', item_label: '', item_value: '', is_active: true })
const filteredItems = computed(() => {
  if (!query.dict_type) return items.value
  return items.value.filter((item) => item.dict_type.includes(query.dict_type))
})

async function loadItems() {
  loading.value = true
  try {
    items.value = await listAllDictionaryItems(false)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  Object.assign(form, { dict_type: query.dict_type || '', item_label: '', item_value: '', is_active: true })
  visible.value = true
}

function openEdit(row: DictionaryItem) {
  editing.value = row
  Object.assign(form, row)
  visible.value = true
}

async function save() {
  saving.value = true
  try {
    if (editing.value) {
      await updateDictionaryItem(editing.value.id, form)
    } else {
      await createDictionaryItem(form)
    }
    ElMessage.success('已保存')
    visible.value = false
    await loadItems()
  } finally {
    saving.value = false
  }
}

async function changeActive(id: number, isActive: boolean) {
  await setDictionaryActive(id, isActive)
  await loadItems()
}

onMounted(loadItems)
</script>
