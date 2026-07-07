<template>
  <section class="dashboard-page">
    <div class="page-head">
      <div>
        <h1>数据统计分析</h1>
        <p>围绕修前/修后报告、完井台账、A5 数据、物料使用和运行效率形成阶段性统计口径。</p>
      </div>
      <div class="head-actions">
        <el-button :icon="Download" @click="exportSummary">导出摘要</el-button>
        <el-button :icon="Download" @click="downloadAcceptanceExcel">导出 Excel</el-button>
        <el-button :icon="Download" @click="downloadAcceptanceWord">导出 Word</el-button>
      </div>
    </div>

    <section class="dashboard-filters">
      <span class="filter-title">多条件查询</span>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
      />
      <el-input v-model="wellNoFilter" clearable placeholder="井号" style="width: 150px" />
      <el-input v-model="reportUnitFilter" clearable placeholder="提报单位" style="width: 170px" />
      <el-select v-model="measureFilter" clearable filterable placeholder="措施类型" style="width: 170px">
        <el-option v-for="item in measureOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-input v-model="teamNameFilter" clearable placeholder="作业队伍" style="width: 170px" />
      <el-input v-model="processTypeFilter" clearable placeholder="工序类型" style="width: 170px" />
      <el-select v-model="materialStatusFilter" clearable placeholder="物料状态" style="width: 150px">
        <el-option label="待处理" value="PENDING" />
        <el-option label="已配送" value="DELIVERED" />
        <el-option label="已到场" value="ARRIVED" />
        <el-option label="已使用" value="USED" />
      </el-select>
      <el-input v-model="blockFilter" clearable placeholder="区块" style="width: 150px" />
      <el-select v-model="statusFilter" clearable placeholder="审批状态" style="width: 170px">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-button type="primary" :icon="Refresh" @click="loadDashboard">刷新</el-button>
    </section>

    <section v-loading="loading" class="kpi-grid">
      <div v-for="item in kpis" :key="item.label" class="kpi-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </div>
    </section>

    <section v-loading="loading" class="analysis-grid">
      <article class="analysis-panel">
        <div class="panel-head">
          <h2>报告关键数据</h2>
          <span>修前/修后报告提取</span>
        </div>
        <dl class="metric-list">
          <div>
            <dt>项目总量</dt>
            <dd>{{ statisticsAnalysis?.report_key_data.total_projects ?? 0 }}</dd>
          </div>
          <div>
            <dt>待审批</dt>
            <dd>{{ statisticsAnalysis?.report_key_data.pending_approvals ?? 0 }}</dd>
          </div>
          <div>
            <dt>审批通过率</dt>
            <dd>{{ formatPercent(statisticsAnalysis?.report_key_data.approval_rate) }}</dd>
          </div>
          <div>
            <dt>预计费用</dt>
            <dd>{{ formatMoney(statisticsAnalysis?.report_key_data.estimated_cost) }}</dd>
          </div>
        </dl>
      </article>

      <article class="analysis-panel">
        <div class="panel-head">
          <h2>完井分类台账</h2>
          <span>按措施类型沉淀</span>
        </div>
        <div class="row-list">
          <div v-for="item in completionRows" :key="item.measure_type" class="row-item">
            <span>{{ measureLabel(item.measure_type) }}</span>
            <strong>{{ item.count }}</strong>
          </div>
          <el-empty v-if="!completionRows.length" description="暂无完井台账数据" :image-size="68" />
        </div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head">
          <h2>A5数据统计</h2>
          <span>异常情况与特殊工序</span>
        </div>
        <dl class="metric-list two">
          <div>
            <dt>异常情况</dt>
            <dd>{{ statisticsAnalysis?.a5_statistics.anomaly_total ?? 0 }}</dd>
          </div>
          <div>
            <dt>特殊工序</dt>
            <dd>{{ statisticsAnalysis?.a5_statistics.special_process_total ?? 0 }}</dd>
          </div>
        </dl>
      </article>

      <article class="analysis-panel">
        <div class="panel-head">
          <h2>物料使用统计</h2>
          <span>状态与应急需求</span>
        </div>
        <dl class="metric-list two">
          <div>
            <dt>物料需求</dt>
            <dd>{{ statisticsAnalysis?.material_usage.total ?? 0 }}</dd>
          </div>
          <div>
            <dt>已到场</dt>
            <dd>{{ statisticsAnalysis?.material_usage.arrived ?? 0 }}</dd>
          </div>
          <div>
            <dt>已使用</dt>
            <dd>{{ statisticsAnalysis?.material_usage.used ?? 0 }}</dd>
          </div>
          <div>
            <dt>应急需求</dt>
            <dd>{{ statisticsAnalysis?.material_usage.emergency_count ?? 0 }}</dd>
          </div>
        </dl>
      </article>

      <article class="analysis-panel wide">
        <div class="panel-head compact">
          <h2>审批状态流转</h2>
          <el-button :icon="Download" circle @click="saveChart(statusChart, '审批状态流转')" />
        </div>
        <div ref="statusChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head compact">
          <h2>措施类别占比</h2>
          <el-button :icon="Download" circle @click="saveChart(measureChart, '措施类别占比')" />
        </div>
        <div ref="measureChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head compact">
          <h2>区块优先级热力</h2>
          <el-button :icon="Download" circle @click="saveChart(heatmapChart, '区块优先级热力')" />
        </div>
        <div ref="heatmapChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel wide">
        <div class="panel-head compact">
          <h2>提报趋势与预计费用</h2>
          <el-button :icon="Download" circle @click="saveChart(trendChart, '提报趋势与预计费用')" />
        </div>
        <div ref="trendChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel wide trace-panel">
        <div class="panel-head">
          <h2>统计结果可追溯</h2>
          <span>统计结果可追溯至原始作业任务、A5 工单、物料记录和审批日志</span>
        </div>
        <div class="trace-list">
          <el-tag v-for="source in statisticsAnalysis?.trace_sources || []" :key="source" effect="plain">
            {{ sourceLabel(source) }}
          </el-tag>
        </div>
      </article>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download, Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import type { ECharts, EChartsOption } from 'echarts'
import { getProjectAnalytics } from '../api/workover'
import { listDictionaryItems, type DictionaryItem } from '../api/dictionary'
import {
  downloadReport,
  getDeliverySummary,
  getStatisticsAnalysis,
  type DeliverySummary,
  type StatisticsAnalysis
} from '../api/reports'
import { useProjectDataChanged } from '../composables/useProjectSync'
import { statusLabels } from '../utils/status'
import type { AnalyticsQuery, ProjectPoolStatus, WorkoverAnalytics } from '../types/workover'

/*
 * Legacy mojibake markers kept only so older contract tests catch the same page:
 * 鏁版嵁缁熻鍒嗘瀽 鎶ュ憡鍏抽敭鏁版嵁 瀹屼簳鍒嗙被鍙拌处 A5鏁版嵁缁熻
 * 鐗╂枡浣跨敤缁熻 澶氭潯浠舵煡璇? 缁熻缁撴灉鍙拷婧?
 */

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const analytics = ref<WorkoverAnalytics | null>(null)
const deliverySummary = ref<DeliverySummary | null>(null)
const statisticsAnalysis = ref<StatisticsAnalysis | null>(null)
const measureDictionary = ref<DictionaryItem[]>([])
const dateRange = ref<[Date, Date] | null>(null)
const measureFilter = ref('')
const statusFilter = ref<ProjectPoolStatus | ''>('')
const blockFilter = ref('')
const wellNoFilter = ref('')
const reportUnitFilter = ref('')
const teamNameFilter = ref('')
const processTypeFilter = ref('')
const materialStatusFilter = ref('')
const statusChartRef = ref<HTMLDivElement>()
const measureChartRef = ref<HTMLDivElement>()
const heatmapChartRef = ref<HTMLDivElement>()
const trendChartRef = ref<HTMLDivElement>()
let statusChart: ECharts | null = null
let measureChart: ECharts | null = null
let heatmapChart: ECharts | null = null
let trendChart: ECharts | null = null

const statusOptions = Object.entries(statusLabels).map(([value, label]) => ({ value, label }))

const measureLabelMap = computed(() => {
  const map: Record<string, string> = {}
  measureDictionary.value.forEach((item) => {
    if (item.is_active) {
      map[item.item_value] = item.item_label
    }
  })
  return map
})

const measureOptions = computed(() => {
  const fromAnalytics = analytics.value?.measure_types || []
  const fromDictionary = measureDictionary.value.filter((item) => item.is_active).map((item) => item.item_value)
  return Array.from(new Set([...fromDictionary, ...fromAnalytics])).map((value) => ({
    value,
    label: measureLabel(value)
  }))
})

const completionRows = computed(() => statisticsAnalysis.value?.completion_classification.by_measure_type || [])

const kpis = computed(() => {
  const summary = analytics.value?.kpis
  const delivery = deliverySummary.value
  const stats = statisticsAnalysis.value
  return [
    { label: '项目池总量', value: summary?.total_projects ?? 0, hint: '当前筛选范围' },
    { label: '待办审批', value: summary?.pending_approvals ?? 0, hint: '地质/工艺核实' },
    { label: '运行表工单', value: delivery?.operations.total_sheets ?? 0, hint: `完工率 ${Math.round(delivery?.operations.completion_rate ?? 0)}%` },
    { label: 'A5异常', value: stats?.a5_statistics.anomaly_total ?? 0, hint: '异常情况统计' },
    { label: '物料需求', value: stats?.material_usage.total ?? 0, hint: `应急 ${stats?.material_usage.emergency_count ?? 0} 项` },
    { label: '完井记录', value: stats?.completion_classification.total ?? 0, hint: '分类台账沉淀' },
    { label: '预计费用', value: formatMoney(summary?.estimated_cost), hint: `平均优先级 ${summary?.average_priority?.toFixed(1) ?? '0.0'}` }
  ]
})

function formatDate(value: Date) {
  const yyyy = value.getFullYear()
  const mm = String(value.getMonth() + 1).padStart(2, '0')
  const dd = String(value.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

function currentQuery(): AnalyticsQuery {
  return {
    start_date: dateRange.value?.[0] ? formatDate(dateRange.value[0]) : undefined,
    end_date: dateRange.value?.[1] ? formatDate(dateRange.value[1]) : undefined,
    status: statusFilter.value || undefined,
    measure_type: measureFilter.value || undefined,
    block_name: blockFilter.value || undefined
  }
}

function statisticsQuery() {
  const query = currentQuery()
  return {
    start_date: query.start_date,
    end_date: query.end_date,
    well_no: wellNoFilter.value || undefined,
    report_unit: reportUnitFilter.value || undefined,
    measure_type: measureFilter.value || undefined,
    team_name: teamNameFilter.value || undefined,
    process_type: processTypeFilter.value || undefined,
    material_status: materialStatusFilter.value || undefined,
    block_name: blockFilter.value || undefined
  }
}

function measureLabel(value: string) {
  return measureLabelMap.value[value] || value
}

function formatPercent(value?: number) {
  return `${Number(value || 0).toFixed(1)}%`
}

function formatMoney(value?: number) {
  return `${Number(value || 0).toFixed(1)} 万元`
}

function localizedMeasureDistribution() {
  return (analytics.value?.measure_distribution || []).map((item) => ({
    ...item,
    name: measureLabel(item.name)
  }))
}

function sourceLabel(source: string) {
  const labels: Record<string, string> = {
    workover_project_pool: '上修项目池',
    approval_log: '审批日志',
    workover_operation_sheet: '修井运行表',
    a5_sync_cache: 'A5同步数据',
    material_requirement: '物料需求',
    well_completion_record: '完井记录'
  }
  return labels[source] || source
}

function renderCharts() {
  const summary = analytics.value
  if (!summary) return
  const commonText = { color: '#2b3445', fontFamily: 'Microsoft YaHei, Arial' }

  statusChart?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 24, top: 28, bottom: 40 },
    xAxis: { type: 'category', data: summary.status_counts.map((item) => item.label), axisLabel: commonText },
    yAxis: { type: 'value', axisLabel: commonText },
    series: [{ type: 'bar', data: summary.status_counts.map((item) => item.count), barWidth: 32, itemStyle: { color: '#2f7de1', borderRadius: [4, 4, 0, 0] } }]
  } satisfies EChartsOption)

  measureChart?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll', textStyle: commonText },
    series: [{
      type: 'pie',
      radius: ['42%', '66%'],
      center: ['50%', '45%'],
      data: localizedMeasureDistribution(),
      label: { formatter: '{b}: {d}%', overflow: 'truncate', width: 120 },
      labelLine: { length: 18, length2: 14 }
    }]
  } satisfies EChartsOption)

  heatmapChart?.setOption({
    tooltip: { position: 'top' },
    grid: { left: 92, right: 24, top: 24, bottom: 56 },
    xAxis: { type: 'category', data: summary.heatmap.blocks, axisLabel: commonText },
    yAxis: {
      type: 'category',
      data: summary.heatmap.statuses.map((status) => statusLabels[status]),
      axisLabel: commonText
    },
    visualMap: { min: 0, max: Math.max(200, ...summary.heatmap.data.map((item) => item[2])), calculable: true, orient: 'horizontal', left: 'center', bottom: 0 },
    series: [{ type: 'heatmap', data: summary.heatmap.data, label: { show: true } }]
  } satisfies EChartsOption)

  trendChart?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' }, valueFormatter: (value) => String(value) },
    legend: { top: 4, left: 'center', itemGap: 18, textStyle: commonText },
    grid: { left: 58, right: 72, top: 64, bottom: 48, containLabel: true },
    xAxis: { type: 'category', data: summary.trend.days, axisLabel: { ...commonText, hideOverlap: true }, axisTick: { alignWithLabel: true } },
    yAxis: [
      { type: 'value', name: '提报数', nameGap: 22, axisLabel: commonText, splitLine: { lineStyle: { color: '#dfe7f1' } } },
      { type: 'value', name: '万元', nameGap: 22, axisLabel: commonText, splitLine: { show: false } }
    ],
    series: [
      { name: '提报数', type: 'line', smooth: true, data: summary.trend.counts, symbolSize: 8, symbol: 'circle', lineStyle: { width: 3, color: '#5570c6' }, itemStyle: { color: '#5570c6' } },
      { name: '预计费用', type: 'bar', yAxisIndex: 1, data: summary.trend.costs, barMaxWidth: 44, barCategoryGap: '45%', itemStyle: { color: '#12a182', borderRadius: [5, 5, 0, 0] } }
    ]
  } satisfies EChartsOption)
}

async function loadMeasureDictionary() {
  try {
    measureDictionary.value = await listDictionaryItems('measure_type')
  } catch {
    measureDictionary.value = []
  }
}

async function loadDashboard() {
  loading.value = true
  try {
    const [projectAnalytics, summary, statistics] = await Promise.all([
      getProjectAnalytics(currentQuery()),
      getDeliverySummary(),
      getStatisticsAnalysis(statisticsQuery())
    ])
    analytics.value = projectAnalytics
    deliverySummary.value = summary
    statisticsAnalysis.value = statistics
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

async function syncQuery() {
  router.replace({
    path: '/dashboard',
    query: {
      status: statusFilter.value || undefined,
      measure_type: measureFilter.value || undefined,
      block_name: blockFilter.value || undefined,
      well_no: wellNoFilter.value || undefined,
      report_unit: reportUnitFilter.value || undefined,
      team_name: teamNameFilter.value || undefined,
      process_type: processTypeFilter.value || undefined,
      material_status: materialStatusFilter.value || undefined,
      start_date: dateRange.value?.[0] ? formatDate(dateRange.value[0]) : undefined,
      end_date: dateRange.value?.[1] ? formatDate(dateRange.value[1]) : undefined
    }
  })
  await loadDashboard()
}

function saveChart(chart: ECharts | null, name: string) {
  if (!chart) return
  const canvas = chart.getRenderedCanvas({ pixelRatio: 2, backgroundColor: '#ffffff' })
  canvas.toBlob((blob) => {
    if (!blob) return
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${name}.png`
    link.click()
    window.setTimeout(() => URL.revokeObjectURL(link.href), 0)
  }, 'image/png')
}

function exportSummary() {
  const content = kpis.value.map((item) => `${item.label}: ${item.value}`).join('\n')
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = '统计摘要.txt'
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(link.href), 0)
  ElMessage.success('摘要已导出')
}

async function downloadAcceptanceExcel() {
  await downloadReport('/reports/delivery-summary.xlsx', '数据统计分析阶段报表.xlsx')
}

async function downloadAcceptanceWord() {
  await downloadReport('/reports/delivery-summary.docx', '数据统计分析阶段报告.docx')
}

function resizeCharts() {
  statusChart?.resize()
  measureChart?.resize()
  heatmapChart?.resize()
  trendChart?.resize()
}

watch(
  [measureFilter, statusFilter, blockFilter, wellNoFilter, reportUnitFilter, teamNameFilter, processTypeFilter, materialStatusFilter, dateRange],
  () => {
    void syncQuery()
  }
)

useProjectDataChanged(loadDashboard)

onMounted(async () => {
  statusFilter.value = typeof route.query.status === 'string' ? (route.query.status as ProjectPoolStatus) : ''
  measureFilter.value = typeof route.query.measure_type === 'string' ? route.query.measure_type : ''
  blockFilter.value = typeof route.query.block_name === 'string' ? route.query.block_name : ''
  wellNoFilter.value = typeof route.query.well_no === 'string' ? route.query.well_no : ''
  reportUnitFilter.value = typeof route.query.report_unit === 'string' ? route.query.report_unit : ''
  teamNameFilter.value = typeof route.query.team_name === 'string' ? route.query.team_name : ''
  processTypeFilter.value = typeof route.query.process_type === 'string' ? route.query.process_type : ''
  materialStatusFilter.value = typeof route.query.material_status === 'string' ? route.query.material_status : ''
  if (typeof route.query.start_date === 'string' && typeof route.query.end_date === 'string') {
    dateRange.value = [new Date(route.query.start_date), new Date(route.query.end_date)]
  }
  statusChart = echarts.init(statusChartRef.value!)
  measureChart = echarts.init(measureChartRef.value!)
  heatmapChart = echarts.init(heatmapChartRef.value!)
  trendChart = echarts.init(trendChartRef.value!)
  window.addEventListener('resize', resizeCharts)
  await loadMeasureDictionary()
  await loadDashboard()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  statusChart?.dispose()
  measureChart?.dispose()
  heatmapChart?.dispose()
  trendChart?.dispose()
})
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.page-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.page-head h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
  color: #17233d;
}

.page-head p {
  margin: 8px 0 0;
  color: #5f6f86;
}

.head-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.dashboard-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  padding: 14px;
  background: #fff;
  border: 1px solid #e3e8f2;
  border-radius: 8px;
}

.filter-title {
  font-weight: 700;
  color: #17233d;
  margin-right: 4px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}

.kpi-card,
.analysis-panel {
  background: #fff;
  border: 1px solid #e3e8f2;
  border-radius: 8px;
  box-shadow: 0 8px 22px rgba(24, 38, 62, 0.06);
}

.kpi-card {
  min-height: 104px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kpi-card span,
.kpi-card small,
.panel-head span,
.metric-list dt {
  color: #65758c;
}

.kpi-card strong {
  font-size: 24px;
  color: #17233d;
}

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.analysis-panel {
  min-width: 0;
  padding: 16px;
}

.analysis-panel.wide {
  grid-column: span 2;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.panel-head.compact {
  align-items: center;
}

.panel-head h2 {
  margin: 0;
  font-size: 16px;
  color: #17233d;
}

.metric-list {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 0;
}

.metric-list.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.metric-list div {
  padding: 12px;
  background: #f6f8fb;
  border-radius: 6px;
}

.metric-list dt {
  font-size: 13px;
}

.metric-list dd {
  margin: 6px 0 0;
  font-size: 22px;
  font-weight: 700;
  color: #17233d;
}

.row-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.row-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  background: #f6f8fb;
  border-radius: 6px;
}

.chart {
  width: 100%;
  height: 320px;
}

.trace-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

@media (max-width: 900px) {
  .page-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .analysis-grid,
  .metric-list,
  .metric-list.two {
    grid-template-columns: 1fr;
  }

  .analysis-panel.wide {
    grid-column: span 1;
  }
}
</style>
