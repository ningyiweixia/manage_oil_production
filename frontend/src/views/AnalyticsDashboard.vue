<template>
  <section class="dashboard-page">
    <div class="page-head">
      <div>
        <h1>数据统计分析</h1>
        <p>面向生产分析、管理复盘和阶段汇报，统一呈现项目、运行、A5、物料、完井统计结果。</p>
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
      <el-input v-model="processTypeFilter" clearable placeholder="A5工序类型" style="width: 170px" />
      <el-select v-model="materialStatusFilter" clearable placeholder="物料状态" style="width: 150px">
        <el-option label="待处理" value="PENDING" />
        <el-option label="已审核" value="APPROVED" />
        <el-option label="已计划" value="PLANNED" />
        <el-option label="已出库" value="DELIVERED" />
        <el-option label="已到场" value="ARRIVED" />
        <el-option label="已使用" value="USED" />
      </el-select>
      <el-input v-model="blockFilter" clearable placeholder="区块" style="width: 150px" />
      <el-select v-model="statusFilter" clearable placeholder="审批状态" style="width: 170px">
        <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
      </el-select>
      <el-button type="primary" :icon="Refresh" @click="loadDashboard">刷新</el-button>
    </section>

    <section v-loading="loading && !stats" class="kpi-grid">
      <div v-for="item in kpis" :key="item.label" class="kpi-card">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
        <small>{{ item.hint }}</small>
      </div>
    </section>

    <section v-loading="loading && !stats" class="section-grid">
      <article class="analysis-panel wide">
        <div class="panel-head">
          <div>
            <h2>项目总览</h2>
            <span>项目池、审批状态、措施结构和预计费用</span>
          </div>
        </div>
        <dl class="metric-list">
          <div>
            <dt>项目总量</dt>
            <dd>{{ stats?.overview_kpis?.total_projects ?? 0 }}</dd>
          </div>
          <div>
            <dt>待审批</dt>
            <dd>{{ stats?.overview_kpis?.pending_approvals ?? 0 }}</dd>
          </div>
          <div>
            <dt>审批通过率</dt>
            <dd>{{ formatPercent(stats?.overview_kpis?.approval_rate) }}</dd>
          </div>
          <div>
            <dt>预计费用</dt>
            <dd>{{ formatMoney(stats?.overview_kpis?.estimated_cost) }}</dd>
          </div>
        </dl>
      </article>

      <article class="analysis-panel">
        <div class="panel-head compact">
          <h2>审批状态柱状图</h2>
          <el-button :icon="Download" circle @click="saveChart(approvalChart, '审批状态柱状图')" />
        </div>
        <div ref="approvalChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head compact">
          <h2>措施类型占比</h2>
          <el-button :icon="Download" circle @click="saveChart(measureChart, '措施类型占比')" />
        </div>
        <div ref="measureChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head">
          <div>
            <h2>作业运行效率</h2>
            <span>运行表工单、派工率、完工率和队伍工作量</span>
          </div>
        </div>
        <dl class="metric-list two">
          <div>
            <dt>运行表工单</dt>
            <dd>{{ stats?.operation_efficiency?.total_sheets ?? 0 }}</dd>
          </div>
          <div>
            <dt>派工率</dt>
            <dd>{{ formatPercent(stats?.operation_efficiency?.dispatch_rate) }}</dd>
          </div>
          <div>
            <dt>完工率</dt>
            <dd>{{ formatPercent(stats?.operation_efficiency?.completion_rate) }}</dd>
          </div>
          <div>
            <dt>A5已同步</dt>
            <dd>{{ stats?.operation_efficiency?.runtime_focus?.a5_synced ?? 0 }}</dd>
          </div>
        </dl>
      </article>

      <article class="analysis-panel">
        <div class="panel-head compact">
          <h2>队伍工作量排行</h2>
          <el-button :icon="Download" circle @click="saveChart(teamChart, '队伍工作量排行')" />
        </div>
        <div ref="teamChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head">
          <div>
            <h2>A5异常与特殊工序</h2>
            <span>A5异常、特殊工序和同步趋势</span>
          </div>
        </div>
        <dl class="metric-list two">
          <div>
            <dt>A5异常</dt>
            <dd>{{ stats?.a5_statistics?.anomaly_total ?? 0 }}</dd>
          </div>
          <div>
            <dt>特殊工序</dt>
            <dd>{{ stats?.a5_statistics?.special_process_total ?? 0 }}</dd>
          </div>
        </dl>
      </article>

      <article class="analysis-panel">
        <div class="panel-head compact">
          <h2>A5异常趋势</h2>
          <el-button :icon="Download" circle @click="saveChart(a5TrendChart, 'A5异常趋势')" />
        </div>
        <div ref="a5TrendChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head">
          <div>
            <h2>物料使用闭环</h2>
            <span>需求、出库、到场、使用和异常情况</span>
          </div>
        </div>
        <dl class="metric-list two">
          <div>
            <dt>物料需求</dt>
            <dd>{{ stats?.material_usage?.total ?? 0 }}</dd>
          </div>
          <div>
            <dt>已到场</dt>
            <dd>{{ stats?.material_usage?.arrived ?? 0 }}</dd>
          </div>
          <div>
            <dt>已使用</dt>
            <dd>{{ stats?.material_usage?.used ?? 0 }}</dd>
          </div>
          <div>
            <dt>使用率</dt>
            <dd>{{ formatPercent(stats?.material_usage?.usage_rate) }}</dd>
          </div>
        </dl>
      </article>

      <article class="analysis-panel">
        <div class="panel-head compact">
          <h2>物料状态分布</h2>
          <el-button :icon="Download" circle @click="saveChart(materialChart, '物料状态分布')" />
        </div>
        <div ref="materialChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head">
          <div>
            <h2>完井分类台账</h2>
            <span>按措施类型沉淀分类台账</span>
          </div>
        </div>
        <div class="row-list">
          <div v-for="item in stats?.completion_classification?.by_measure_type || []" :key="item.measure_type" class="row-item">
            <span>{{ measureLabel(item.measure_type) }}</span>
            <strong>{{ item.count }}</strong>
          </div>
          <el-empty v-if="!(stats?.completion_classification?.by_measure_type || []).length" description="暂无完井台账数据" :image-size="68" />
        </div>
      </article>

      <article class="analysis-panel">
        <div class="panel-head compact">
          <h2>完井措施分类</h2>
          <el-button :icon="Download" circle @click="saveChart(completionChart, '完井措施分类')" />
        </div>
        <div ref="completionChartRef" class="chart"></div>
      </article>

      <article class="analysis-panel wide">
        <div class="panel-head compact">
          <h2>区块/状态热力图</h2>
          <el-button :icon="Download" circle @click="saveChart(heatmapChart, '区块状态热力图')" />
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
          <div>
            <h2>统计结果可追溯</h2>
            <span>统计结果可追溯至原始作业任务、A5工单、物料记录、完井记录和审批日志</span>
          </div>
        </div>
        <div class="trace-list">
          <el-tag v-for="source in stats?.trace_sources || []" :key="source" effect="plain">
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
import { listDictionaryItems, type DictionaryItem } from '../api/dictionary'
import { downloadReport, getStatisticsAnalysis, type StatisticsAnalysis } from '../api/reports'
import { useProjectDataChanged } from '../composables/useProjectSync'
import { statusLabels } from '../utils/status'
import type { ProjectPoolStatus } from '../types/workover'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const stats = ref<StatisticsAnalysis | null>(null)
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
const isRestoringQuery = ref(true)
let latestLoadId = 0

const approvalChartRef = ref<HTMLDivElement>()
const measureChartRef = ref<HTMLDivElement>()
const teamChartRef = ref<HTMLDivElement>()
const a5TrendChartRef = ref<HTMLDivElement>()
const materialChartRef = ref<HTMLDivElement>()
const completionChartRef = ref<HTMLDivElement>()
const heatmapChartRef = ref<HTMLDivElement>()
const trendChartRef = ref<HTMLDivElement>()

let approvalChart: ECharts | null = null
let measureChart: ECharts | null = null
let teamChart: ECharts | null = null
let a5TrendChart: ECharts | null = null
let materialChart: ECharts | null = null
let completionChart: ECharts | null = null
let heatmapChart: ECharts | null = null
let trendChart: ECharts | null = null

const statusOptions = Object.entries(statusLabels).map(([value, label]) => ({ value, label }))

const measureLabelMap = computed(() => {
  const map: Record<string, string> = {}
  measureDictionary.value.forEach((item) => {
    if (item.is_active) map[item.item_value] = item.item_label
  })
  return map
})

const measureOptions = computed(() => {
  const fromStats = stats.value?.chart_series?.measure_distribution?.map((item) => item.name) || []
  const fromDictionary = measureDictionary.value.filter((item) => item.is_active).map((item) => item.item_value)
  return Array.from(new Set([...fromDictionary, ...fromStats])).map((value) => ({ value, label: measureLabel(value) }))
})

const kpis = computed(() => {
  const overview = stats.value?.overview_kpis
  return [
    { label: '项目池总量', value: overview?.total_projects ?? 0, hint: '当前筛选范围' },
    { label: '待办审批', value: overview?.pending_approvals ?? 0, hint: '地质/工艺核实' },
    { label: '运行表工单', value: overview?.operation_sheets ?? 0, hint: '派工与施工跟踪' },
    { label: 'A5异常', value: overview?.a5_anomalies ?? 0, hint: '异常情况统计' },
    { label: '物料需求', value: overview?.material_requirements ?? 0, hint: '物料闭环台账' },
    { label: '完井记录', value: overview?.completion_records ?? 0, hint: '分类台账沉淀' },
    { label: '预计费用', value: formatMoney(overview?.estimated_cost), hint: '阶段性汇报口径' }
  ]
})

function formatDate(value: Date) {
  const yyyy = value.getFullYear()
  const mm = String(value.getMonth() + 1).padStart(2, '0')
  const dd = String(value.getDate()).padStart(2, '0')
  return `${yyyy}-${mm}-${dd}`
}

function statisticsQuery() {
  return {
    start_date: dateRange.value?.[0] ? formatDate(dateRange.value[0]) : undefined,
    end_date: dateRange.value?.[1] ? formatDate(dateRange.value[1]) : undefined,
    well_no: wellNoFilter.value || undefined,
    report_unit: reportUnitFilter.value || undefined,
    measure_type: measureFilter.value || undefined,
    team_name: teamNameFilter.value || undefined,
    process_type: processTypeFilter.value || undefined,
    material_status: materialStatusFilter.value || undefined,
    block_name: blockFilter.value || undefined,
    status: statusFilter.value || undefined
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

function sourceLabel(source: string) {
  const labels: Record<string, string> = {
    workover_project_pool: '上修项目池',
    approval_log: '审批日志',
    workover_operation_sheet: '修井运行表',
    a5_sync_cache: 'A5同步数据',
    material_requirement: '物料记录',
    well_completion_record: '完井记录'
  }
  return labels[source] || source
}

function named(items?: Array<{ name: string; value: number }>) {
  return items || []
}

function renderCharts() {
  const series = stats.value?.chart_series
  if (!series) return
  const commonText = { color: '#2b3445', fontFamily: 'Microsoft YaHei, Arial' }

  approvalChart?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 20, top: 28, bottom: 48 },
    xAxis: { type: 'category', data: (series.approval_status || []).map((item) => item.name), axisLabel: { ...commonText, interval: 0, rotate: 18 } },
    yAxis: { type: 'value', axisLabel: commonText },
    series: [{ type: 'bar', data: (series.approval_status || []).map((item) => item.value), itemStyle: { color: '#2f7de1', borderRadius: [4, 4, 0, 0] } }]
  } satisfies EChartsOption)

  measureChart?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll', textStyle: commonText },
    series: [{ type: 'pie', radius: ['42%', '66%'], center: ['50%', '43%'], data: named(series.measure_distribution).map((item) => ({ ...item, name: measureLabel(item.name) })) }]
  } satisfies EChartsOption)

  teamChart?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 88, right: 20, top: 28, bottom: 28 },
    xAxis: { type: 'value', axisLabel: commonText },
    yAxis: { type: 'category', data: (series.team_workload_rank || []).map((item) => item.team_name), axisLabel: commonText },
    series: [{ type: 'bar', data: (series.team_workload_rank || []).map((item) => item.sheet_count), itemStyle: { color: '#12a182' } }]
  } satisfies EChartsOption)

  a5TrendChart?.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: commonText },
    grid: { left: 42, right: 20, top: 48, bottom: 34 },
    xAxis: { type: 'category', data: series.a5_anomaly_trend?.days || [], axisLabel: commonText },
    yAxis: { type: 'value', axisLabel: commonText },
    series: [
      { name: '异常情况', type: 'line', smooth: true, data: series.a5_anomaly_trend?.anomaly_counts || [] },
      { name: '特殊工序', type: 'line', smooth: true, data: series.a5_anomaly_trend?.process_counts || [] }
    ]
  } satisfies EChartsOption)

  materialChart?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll', textStyle: commonText },
    series: [{ type: 'pie', radius: '62%', center: ['50%', '43%'], data: named(series.material_status_distribution) }]
  } satisfies EChartsOption)

  completionChart?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, type: 'scroll', textStyle: commonText },
    series: [{ type: 'pie', radius: ['38%', '64%'], center: ['50%', '43%'], data: named(series.completion_measure_distribution).map((item) => ({ ...item, name: measureLabel(item.name) })) }]
  } satisfies EChartsOption)

  const heatmap = series.block_status_heatmap || { blocks: [], statuses: [], data: [] }
  heatmapChart?.setOption({
    tooltip: { position: 'top' },
    grid: { left: 100, right: 24, top: 26, bottom: 54 },
    xAxis: { type: 'category', data: heatmap.blocks || [], axisLabel: commonText },
    yAxis: { type: 'category', data: (heatmap.statuses || []).map((status) => statusLabels[status as ProjectPoolStatus] || status), axisLabel: commonText },
    visualMap: { min: 0, max: Math.max(10, ...(heatmap.data || []).map((item) => item[2])), calculable: true, orient: 'horizontal', left: 'center', bottom: 0 },
    series: [{ type: 'heatmap', data: heatmap.data || [], label: { show: true } }]
  } satisfies EChartsOption)

  const trend = series.submission_trend || { days: [], counts: [], costs: [] }
  trendChart?.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { top: 4, textStyle: commonText },
    grid: { left: 58, right: 72, top: 58, bottom: 42, containLabel: true },
    xAxis: { type: 'category', data: trend.days || [], axisLabel: commonText },
    yAxis: [
      { type: 'value', name: '提报数', axisLabel: commonText },
      { type: 'value', name: '万元', axisLabel: commonText }
    ],
    series: [
      { name: '提报数', type: 'line', smooth: true, data: trend.counts || [] },
      { name: '预计费用', type: 'bar', yAxisIndex: 1, data: trend.costs || [], itemStyle: { color: '#5570c6' } }
    ]
  } satisfies EChartsOption)
}

function initCharts() {
  const options = { renderer: 'svg' as const }
  if (approvalChartRef.value) approvalChart = echarts.init(approvalChartRef.value, undefined, options)
  if (measureChartRef.value) measureChart = echarts.init(measureChartRef.value, undefined, options)
  if (teamChartRef.value) teamChart = echarts.init(teamChartRef.value, undefined, options)
  if (a5TrendChartRef.value) a5TrendChart = echarts.init(a5TrendChartRef.value, undefined, options)
  if (materialChartRef.value) materialChart = echarts.init(materialChartRef.value, undefined, options)
  if (completionChartRef.value) completionChart = echarts.init(completionChartRef.value, undefined, options)
  if (heatmapChartRef.value) heatmapChart = echarts.init(heatmapChartRef.value, undefined, options)
  if (trendChartRef.value) trendChart = echarts.init(trendChartRef.value, undefined, options)
}

async function loadMeasureDictionary() {
  try {
    measureDictionary.value = await listDictionaryItems('measure_type')
  } catch {
    measureDictionary.value = []
  }
}

async function loadDashboard() {
  const loadId = ++latestLoadId
  loading.value = true
  try {
    stats.value = await getStatisticsAnalysis(statisticsQuery())
    await nextTick()
    renderCharts()
  } finally {
    if (loadId === latestLoadId) {
      loading.value = false
    }
  }
}

async function syncQuery() {
  await router.replace({ path: '/dashboard', query: statisticsQuery() })
  await loadDashboard()
}

function saveChart(chart: ECharts | null, name: string) {
  if (!chart) return
  const link = document.createElement('a')
  link.href = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#ffffff' })
  link.download = `${name}.png`
  link.click()
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
  approvalChart?.resize()
  measureChart?.resize()
  teamChart?.resize()
  a5TrendChart?.resize()
  materialChart?.resize()
  completionChart?.resize()
  heatmapChart?.resize()
  trendChart?.resize()
}

watch(
  [measureFilter, statusFilter, blockFilter, wellNoFilter, reportUnitFilter, teamNameFilter, processTypeFilter, materialStatusFilter, dateRange],
  () => {
    if (isRestoringQuery.value) return
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
  isRestoringQuery.value = false
  initCharts()
  window.addEventListener('resize', resizeCharts)
  await loadMeasureDictionary()
  await loadDashboard()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeCharts)
  approvalChart?.dispose()
  measureChart?.dispose()
  teamChart?.dispose()
  a5TrendChart?.dispose()
  materialChart?.dispose()
  completionChart?.dispose()
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

.section-grid {
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

  .section-grid,
  .metric-list,
  .metric-list.two {
    grid-template-columns: 1fr;
  }

  .analysis-panel.wide {
    grid-column: span 1;
  }
}
</style>
