<template>
  <main class="mock-a5-page">
    <section class="mock-a5-card">
      <header>
        <div>
          <p class="eyebrow">A5 本地模拟系统</p>
          <h1>措施审核与下发</h1>
          <p>此页面仅在本地演示模式启用，操作会按正式状态机回写修井运行表。</p>
        </div>
        <el-tag type="warning" effect="dark">本地演示</el-tag>
      </header>

      <el-skeleton v-if="loading" :rows="6" animated />
      <el-result v-else-if="errorMessage" icon="error" title="无法打开模拟审核单" :sub-title="errorMessage">
        <template #extra><el-button type="primary" @click="loadReview">重新加载</el-button></template>
      </el-result>
      <template v-else-if="review">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="作业编号">{{ review.operation_no }}</el-descriptions-item>
          <el-descriptions-item label="作业井">{{ review.well_no }}</el-descriptions-item>
          <el-descriptions-item label="承包商队伍">{{ teamLabel }}</el-descriptions-item>
          <el-descriptions-item label="当前状态"><el-tag type="warning">{{ statusLabel }}</el-tag></el-descriptions-item>
          <el-descriptions-item label="措施内容" :span="2">{{ measureLabel }}</el-descriptions-item>
        </el-descriptions>

        <el-form class="review-form" label-position="top">
          <el-form-item label="审核意见">
            <el-input v-model="remark" type="textarea" :rows="4" maxlength="500" show-word-limit placeholder="可填写审核意见；留空将使用模拟系统默认意见" />
          </el-form-item>
        </el-form>

        <el-alert
          v-if="review.status !== 'PENDING_A5'"
          title="该工单已完成本次审核处理，请返回修井运行管理查看最新状态。"
          type="info"
          :closable="false"
          show-icon
        />
        <div class="actions">
          <el-button @click="closePage">返回</el-button>
          <el-button type="danger" :disabled="review.status !== 'PENDING_A5'" :loading="submitting" @click="submit('REJECT')">驳回至待派工</el-button>
          <el-button type="primary" :disabled="review.status !== 'PENDING_A5'" :loading="submitting" @click="submit('DISPATCH')">审核通过并下发</el-button>
        </div>
      </template>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { getA5MockMeasureReview, submitA5MockMeasureReview, type A5MockMeasureReview } from '../api/a5'
import { measureTypeLabel } from '../utils/businessLabels'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const errorMessage = ref('')
const review = ref<A5MockMeasureReview | null>(null)
const remark = ref('')
const token = computed(() => typeof route.query.token === 'string' ? route.query.token : '')
const operationNo = computed(() => typeof route.query.operation_no === 'string' ? route.query.operation_no : '')
const teamLabel = computed(() => review.value?.contractor_name && review.value?.team_name ? `${review.value.contractor_name} / ${review.value.team_name}` : '未分配')
const measureLabel = computed(() => (review.value?.measures || []).map((item) => measureTypeLabel(typeof item.measure_type === 'string' ? item.measure_type : undefined)).join('、') || '未提供')
const statusLabel = computed(() => review.value?.a5_status || '待措施审核')

async function loadReview() {
  loading.value = true
  errorMessage.value = ''
  try {
    if (!token.value || !operationNo.value) throw new Error('缺少 A5 单点登录参数')
    review.value = await getA5MockMeasureReview(token.value, operationNo.value)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '模拟审核单加载失败'
  } finally {
    loading.value = false
  }
}

async function submit(decision: 'DISPATCH' | 'REJECT') {
  if (!review.value) return
  const action = decision === 'DISPATCH' ? '审核通过并下发' : '驳回至待派工'
  await ElMessageBox.confirm(`确认${action}该措施单？`, 'A5 模拟审核', { type: decision === 'DISPATCH' ? 'success' : 'warning' })
  submitting.value = true
  try {
    const result = await submitA5MockMeasureReview({ token: token.value, operation_no: review.value.operation_no, decision, remark: remark.value || undefined })
    ElMessage.success(result.message)
    await loadReview()
  } finally {
    submitting.value = false
  }
}

function closePage() {
  if (window.opener) window.close()
  else router.push('/workover/operation-sheets')
}

onMounted(loadReview)
</script>

<style scoped>
.mock-a5-page { min-height: 100vh; padding: 48px 20px; background: linear-gradient(145deg, #eef5ff, #f7fafc); }
.mock-a5-card { max-width: 820px; margin: 0 auto; padding: 32px; border: 1px solid #dbe5f0; border-radius: 16px; background: #fff; box-shadow: 0 18px 45px rgb(26 60 97 / 12%); }
header { display: flex; justify-content: space-between; gap: 24px; margin-bottom: 28px; }
h1 { margin: 4px 0 8px; color: #17324d; font-size: 26px; }
header p:not(.eyebrow) { margin: 0; color: #667085; }
.eyebrow { margin: 0; color: #3c78c2; font-size: 13px; font-weight: 700; letter-spacing: .08em; }
.review-form { margin-top: 24px; }
.actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }
@media (max-width: 640px) { .mock-a5-page { padding: 16px; } .mock-a5-card { padding: 20px; } header { display: block; } header .el-tag { margin-top: 12px; } .actions { flex-wrap: wrap; } }
</style>
