<template>
  <section class="toolbar">
    <el-form :model="query" inline>
      <el-form-item label="井号">
        <el-input v-model="query.well_no" clearable placeholder="CY2-136" @keyup.enter="loadWorkbench" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :icon="Search" @click="loadWorkbench">查询</el-button>
        <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>
  </section>

  <section class="workflow-strip">
    <div v-for="item in scopeCards" :key="item.name" class="workflow-node clickable" :class="{ active: activeScope === item.name }" @click="switchScope(item.name)">
      <span>{{ item.count }}</span>
      <strong>{{ item.label }}</strong>
      <small>{{ item.desc }}</small>
    </div>
  </section>

  <section class="table-panel">
    <div class="panel-head">
      <div>
        <h2>审核审批工作台</h2>
        <p>按审批节点和处理角色聚合待办、已处理、已驳回与已通过事项。</p>
      </div>
    </div>

    <el-tabs v-model="activeScope" class="approval-tabs" @tab-change="switchScope">
      <el-tab-pane label="我的待办" name="pending" />
      <el-tab-pane label="已处理" name="processed" />
      <el-tab-pane label="已驳回" name="rejected" />
      <el-tab-pane label="已通过" name="approved" />
    </el-tabs>

    <el-table v-loading="loading" :data="tasks" row-key="business_id" empty-text="暂无审批任务">
      <el-table-column label="井号" min-width="110" fixed>
        <template #default="{ row }">
          <strong>{{ row.project.well_no }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="提报单位" min-width="130">
        <template #default="{ row }">{{ row.project.report_unit }}</template>
      </el-table-column>
      <el-table-column label="原因分类" min-width="120">
        <template #default="{ row }">{{ row.project.reason_category || '-' }}</template>
      </el-table-column>
      <el-table-column label="措施摘要" min-width="190" show-overflow-tooltip>
        <template #default="{ row }">{{ row.measure_summary || row.project.reason || '-' }}</template>
      </el-table-column>
      <el-table-column label="资料完整性" min-width="115">
        <template #default="{ row }">
          <el-tag :type="completenessTag(row.project.completeness_status)">{{ completenessLabel(row.project.completeness_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="当前节点" min-width="130">
        <template #default="{ row }">
          <el-tag :type="statusTagType(row.project.status)" effect="light">{{ row.node_label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="停留时长" min-width="105">
        <template #default="{ row }">{{ row.stay_hours }} 小时</template>
      </el-table-column>
      <el-table-column label="最近意见" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">{{ row.last_comment || '-' }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="250" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <el-button text type="primary" @click="openTimeline(row)">审批轨迹</el-button>
            <el-button v-if="canProcess(row, 'APPROVE')" text type="success" @click="openApproval(row, 'APPROVE')">通过</el-button>
            <el-button v-if="canProcess(row, 'REJECT')" text type="warning" @click="openApproval(row, 'REJECT')">驳回</el-button>
            <el-button v-if="canProcess(row, 'RESUBMIT')" text type="success" @click="resubmitRejected(row)">重新提报</el-button>
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
      @current-change="loadTasks"
      @size-change="loadTasks"
    />
  </section>

  <el-dialog v-model="approvalDialogVisible" title="审批处理" width="620px">
    <div v-if="pendingTask" class="approval-context">
      <div>
        <span>井号</span>
        <strong>{{ pendingTask.project.well_no }}</strong>
      </div>
      <div>
        <span>当前节点</span>
        <strong>{{ pendingTask.node_label }}</strong>
      </div>
      <div>
        <span>提报单位</span>
        <strong>{{ pendingTask.project.report_unit }}</strong>
      </div>
      <div>
        <span>资料完整性</span>
        <strong>{{ completenessLabel(pendingTask.project.completeness_status) }}</strong>
      </div>
    </div>
    <el-alert
      v-if="pendingAction === 'APPROVE' && pendingTask?.current_node === 'PENDING_PROCESS_VERIFY'"
      title="通过后将进入运行库"
      type="success"
      show-icon
      :closable="false"
    />
    <el-form label-position="top" class="approval-form">
      <el-form-item v-if="pendingAction === 'APPROVE' && pendingTask?.current_node === 'PENDING_GEOLOGY_VERIFY'" label="核实日产油">
        <el-input-number v-model="approvalExtra.geology_verified_daily_oil" :min="0" :precision="2" :controls="false" style="width: 220px" />
      </el-form-item>
      <template v-if="pendingTask?.current_node === 'PENDING_PROCESS_VERIFY'">
        <el-form-item label="井况核实结论">
          <el-input v-model="approvalExtra.process_well_condition" type="textarea" :rows="3" placeholder="填写井筒、管柱、套损、施工风险等核实结论" />
        </el-form-item>
        <el-form-item label="是否可以上修">
          <el-switch v-model="approvalExtra.process_can_workover" />
        </el-form-item>
      </template>
      <el-form-item :label="pendingAction === 'REJECT' ? '驳回原因' : '处理意见'">
        <el-input v-model="approvalComment" type="textarea" :rows="4" placeholder="填写核实结论、补充要求或审批说明" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="approvalDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="confirmApproval">确认处理</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="timelineVisible" title="审批轨迹" width="560px">
    <el-timeline v-loading="timelineLoading">
      <el-timeline-item v-for="item in timeline" :key="item.id" :timestamp="formatTime(item.created_at)" placement="top">
        <div class="timeline-card">
          <strong>{{ item.node_label }} · {{ item.action_label }}</strong>
          <p>{{ item.comment || '无审批意见' }}</p>
          <small>{{ item.operator_name || item.operator_id || '系统' }}：{{ item.before_status || '-' }} → {{ item.after_status || '-' }}</small>
        </div>
      </el-timeline-item>
    </el-timeline>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Search } from '@element-plus/icons-vue'
import { getApprovalTimeline, listApprovalTasks, processProjectApproval } from '../api/approval'
import { emitProjectDataChanged, useProjectDataChanged } from '../composables/useProjectSync'
import { rejectedAtLabel, statusTagType } from '../utils/status'
import type { ApprovalActionCode, ApprovalTask, ApprovalTaskScope, ApprovalTimelineItem } from '../api/approval'

const route = useRoute()
const router = useRouter()
const activeScope = ref<ApprovalTaskScope>('pending')
const query = reactive({ page: 1, page_size: 10, well_no: '' })
const tasks = ref<ApprovalTask[]>([])
const total = ref(0)
const scopeTotals = reactive<Record<ApprovalTaskScope, number>>({
  pending: 0,
  processed: 0,
  rejected: 0,
  approved: 0
})
const loading = ref(false)
const saving = ref(false)
const approvalDialogVisible = ref(false)
const approvalComment = ref('')
const approvalExtra = reactive<{
  geology_verified_daily_oil: number | null
  process_well_condition: string
  process_can_workover: boolean
}>({
  geology_verified_daily_oil: null,
  process_well_condition: '',
  process_can_workover: true
})
const pendingTask = ref<ApprovalTask | null>(null)
const pendingAction = ref<ApprovalActionCode>('APPROVE')
const timelineVisible = ref(false)
const timelineLoading = ref(false)
const timeline = ref<ApprovalTimelineItem[]>([])
const approvalScopes: ApprovalTaskScope[] = ['pending', 'processed', 'rejected', 'approved']

const scopeCards = computed(() => [
  { name: 'pending' as ApprovalTaskScope, label: '我的待办', desc: '地质与工艺', count: scopeTotals.pending },
  { name: 'processed' as ApprovalTaskScope, label: '已处理', desc: '本人经办', count: scopeTotals.processed },
  { name: 'rejected' as ApprovalTaskScope, label: '已驳回', desc: '待补充', count: scopeTotals.rejected },
  { name: 'approved' as ApprovalTaskScope, label: '已通过', desc: '进入运行库', count: scopeTotals.approved }
])

function completenessLabel(status?: string) {
  if (status === 'COMPLETE') return '完整'
  if (status === 'NEEDS_SUPPLEMENT') return '需补充'
  return '未完整'
}

function completenessTag(status?: string) {
  if (status === 'COMPLETE') return 'success'
  if (status === 'NEEDS_SUPPLEMENT') return 'warning'
  return 'info'
}

function canProcess(row: ApprovalTask, action: ApprovalActionCode) {
  return row.can_process && row.allowed_actions.includes(action)
}

async function loadTasks() {
  loading.value = true
  try {
    const result = await listApprovalTasks({
      scope: activeScope.value,
      page: query.page,
      page_size: query.page_size,
      well_no: query.well_no
    })
    tasks.value = result.items
    total.value = result.total
    scopeTotals[activeScope.value] = result.total
  } finally {
    loading.value = false
  }
}

async function loadScopeTotals() {
  const results = await Promise.all([
    listApprovalTasks({ scope: 'pending', page: 1, page_size: 1, well_no: query.well_no }),
    listApprovalTasks({ scope: 'processed', page: 1, page_size: 1, well_no: query.well_no }),
    listApprovalTasks({ scope: 'rejected', page: 1, page_size: 1, well_no: query.well_no }),
    listApprovalTasks({ scope: 'approved', page: 1, page_size: 1, well_no: query.well_no })
  ])
  approvalScopes.forEach((scope, index) => {
    scopeTotals[scope] = results[index].total
  })
}

async function loadWorkbench() {
  query.page = 1
  await Promise.all([loadTasks(), loadScopeTotals()])
}

function switchScope(name: string | number) {
  activeScope.value = name as ApprovalTaskScope
  query.page = 1
  router.replace({ path: '/approval', query: { scope: activeScope.value } })
  void loadTasks()
}

function resetQuery() {
  query.page = 1
  query.well_no = ''
  void loadWorkbench()
}

function openApproval(row: ApprovalTask, action: ApprovalActionCode) {
  pendingTask.value = row
  pendingAction.value = action
  approvalExtra.geology_verified_daily_oil = null
  approvalExtra.process_well_condition = row.project.process_well_condition || ''
  approvalExtra.process_can_workover = action === 'REJECT' ? false : true
  approvalComment.value = action === 'APPROVE'
    ? row.current_node === 'PENDING_PROCESS_VERIFY'
      ? '核实通过，同意审批，进入运行库。'
      : '核实通过，同意流转至工艺核实。'
    : ''
  approvalDialogVisible.value = true
}

async function confirmApproval() {
  if (!pendingTask.value) return
  if (
    pendingAction.value === 'APPROVE'
    && pendingTask.value.current_node === 'PENDING_GEOLOGY_VERIFY'
    && (approvalExtra.geology_verified_daily_oil === null || Number.isNaN(Number(approvalExtra.geology_verified_daily_oil)))
  ) {
    ElMessage.warning('请填写核实日产油')
    return
  }
  if (
    pendingAction.value === 'APPROVE'
    && pendingTask.value.current_node === 'PENDING_PROCESS_VERIFY'
    && !approvalExtra.process_well_condition.trim()
  ) {
    ElMessage.warning('请填写井况核实结论')
    return
  }
  if (pendingAction.value === 'REJECT' && !approvalComment.value.trim()) {
    ElMessage.warning('驳回时必须填写原因')
    return
  }
  saving.value = true
  try {
    await processProjectApproval(pendingTask.value.business_id, {
      action: pendingAction.value,
      comment: approvalComment.value,
      geology_verified_daily_oil: approvalExtra.geology_verified_daily_oil,
      process_well_condition: approvalExtra.process_well_condition,
      process_can_workover: approvalExtra.process_can_workover
    })
    ElMessage.success(pendingAction.value === 'APPROVE' ? '审批已通过' : '已驳回并记录补充要求')
    approvalDialogVisible.value = false
    emitProjectDataChanged()
    await Promise.all([loadTasks(), loadScopeTotals()])
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.message || '审批操作失败')
  } finally {
    saving.value = false
  }
}

async function resubmitRejected(row: ApprovalTask) {
  const targetName = rejectedAtLabel(row.project.rejected_from_status).replace('驳回', '核实')
  try {
    await ElMessageBox.confirm(`将重新提交至${targetName}，是否继续？`, '重新提报', { type: 'warning' })
  } catch {
    return
  }
  saving.value = true
  try {
    await processProjectApproval(row.business_id, { action: 'RESUBMIT', comment: '补充资料后重新提报' })
    ElMessage.success(`已重新提交至${targetName}`)
    emitProjectDataChanged()
    await Promise.all([loadTasks(), loadScopeTotals()])
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.msg || error?.message || '重新提报失败')
  } finally {
    saving.value = false
  }
}

async function openTimeline(row: ApprovalTask) {
  timelineVisible.value = true
  timelineLoading.value = true
  try {
    timeline.value = await getApprovalTimeline(row.business_type, row.business_id)
  } finally {
    timelineLoading.value = false
  }
}

function formatTime(value: string) {
  return new Date(value).toLocaleString()
}

watch(
  () => route.query.scope,
  (scope) => {
    if (typeof scope === 'string' && scope !== activeScope.value) {
      activeScope.value = scope as ApprovalTaskScope
      query.page = 1
      void loadTasks()
    }
  }
)

useProjectDataChanged(() => { void Promise.all([loadTasks(), loadScopeTotals()]) })

onMounted(() => {
  if (typeof route.query.scope === 'string') activeScope.value = route.query.scope as ApprovalTaskScope
  void Promise.all([loadTasks(), loadScopeTotals()])
})
</script>
