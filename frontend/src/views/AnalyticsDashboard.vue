<template>
  <section class="dashboard-filters">
    <el-date-picker
      v-model="dateRange"
      type="daterange"
      range-separator="至"
      start-placeholder="开始日期"
      end-placeholder="结束日期"
    />
    <el-select v-model="measureFilter" clearable filterable placeholder="措施类别" style="width: 180px">
      <el-option v-for="item in measureOptions" :key="item.value" :label="item.label" :value="item.value" />
    </el-select>
    <el-select v-model="statusFilter" clearable placeholder="审批状态" style="width: 180px">
      <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
    </el-select>
    <el-input v-model="blockFilter" clearable placeholder="区块" style="width: 160px" />
    <el-button type="primary" :icon="Refresh" @click="loadDashboard">刷新</el-button>
    <el-button :icon="Download" @click="exportSummary">导出摘要</el-button>
    <el-button :icon="Download" @click="downloadAcceptanceExcel">导出 Excel</el-button>
    <el-button :icon="Download" @click="downloadAcceptanceWord">导出 Word</el-button>
  </section>

  <section v-loading="loading" class="kpi-grid">
    <div v-for="item in kpis" :key="item.label" class="kpi-card">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
      <small>{{ item.hint }}</small>
    </div>
  </section>

  <section v-loading="loading" class="chart-grid">
    <article class="chart-panel wide">
      <div class="panel-head compact">
        <h2>审批状态流转</h2>
        <el-button :icon="Download" circle @click="saveChart(statusChart, '审批状态流转')" />
      </div>
      <div ref="statusChartRef" class="chart"></div>
    </article>

    <article class="chart-panel">
      <div class="panel-head compact">
        <h2>措施类别占比</h2>
        <el-button :icon="Download" circle @click="saveChart(measureChart, '措施类别占比')" />
      </div>
      <div ref="measureChartRef" class="chart"></div>
    </article>

    <article class="chart-panel">
      <div class="panel-head compact">
        <h2>区块优先级热力</h2>
        <el-button :icon="Download" circle @click="saveChart(heatmapChart, '区块优先级热力')" />
      </div>
      <div ref="heatmapChartRef" class="chart"></div>
    </article>

    <article class="chart-panel wide">
      <div class="panel-head compact">
        <h2>提报趋势与预计费用</h2>
        <el-button :icon="Download" circle @click="saveChart(trendChart, '提报趋势与预计费用')" />
      </div>
      <div ref="trendChartRef" class="chart"></div>
    </article>
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
import { downloadReport, getDeliverySummary, type DeliverySummary } from '../api/reports'
import { useProjectDataChanged } from '../composables/useProjectSync'
import { statusLabels } from '../utils/status'
import type { AnalyticsQuery, ProjectPoolStatus, WorkoverAnalytics } from '../types/workover'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const analytics = ref<WorkoverAnalytics | null>(null)
const deliverySummary = ref<DeliverySummary | null>(null)
const measureDictionary = ref<DictionaryItem[]>([])
const dateRange = ref<[Date, Date] | null>(null)
const measureFilter = ref('')
const statusFilter = ref<ProjectPoolStatus | ''>('')
const blockFilter = ref('')
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

const measureOptions = computed(() => (analytics.value?.measure_types || []).map((value) => ({
  value,
  label: measureLabel(value)
})))

const kpis = computed(() => {
  const summary = analytics.value?.kpis
  const delivery = deliverySummary.value
  if (!summary) {
    return [
      { label: '项目池总量', value: 0, hint: '当前筛选范围' },
      { label: '待办审批', value: 0, hint: '地质/工艺核实' },
      { label: '运行表工单', value: 0, hint: '审批通过后自动入库' },
      { label: '物料需求', value: 0, hint: '配送与到场跟踪' },
      { label: '完井记录', value: 0, hint: '分类台账沉淀' },
      { label: '预计费用', value: '0.0 万', hint: '措施费用汇总' }
    ]
  }
  return [
    { label: '项目池总量', value: summary.total_projects, hint: '当前筛选范围' },
    { label: '待办审批', value: summary.pending_approvals, hint: '地质/工艺核实' },
    { label: '运行表工单', value: delivery?.operations.total_sheets ?? 0, hint: `派工率 ${Math.round(delivery?.operations.dispatch_rate ?? 0)}%` },
    { label: '物料需求', value: delivery?.materials.total ?? 0, hint: `紧急 ${delivery?.materials.emergency_count ?? 0} 项` },
    { label: '完井记录', value: delivery?.completions.total ?? 0, hint: '按措施类型统计' },
    { label: '预计费用', value: `${summary.estimated_cost.toFixed(1)} 万`, hint: `平均优先级 ${summary.average_priority.toFixed(1)}` }
  ]
})

function formatDate(value: Date) {
  // Use local date to avoid timezone offset shifting the day
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

function measureLabel(value: string) {
  return measureLabelMap.value[value] || value
}

function localizedMeasureDistribution() {
  return (analytics.value?.measure_distribution || []).map((item) => ({
    ...item,
    name: measureLabel(item.name)
  }))
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
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      valueFormatter: (value) => String(value)
    },
    legend: { top: 4, left: 'center', itemGap: 18, textStyle: commonText },
    grid: { left: 58, right: 72, top: 64, bottom: 48, containLabel: true },
    xAxis: {
      type: 'category',
      data: summary.trend.days,
      axisLabel: { ...commonText, hideOverlap: true },
      axisTick: { alignWithLabel: true }
    },
    yAxis: [
      { type: 'value', name: '提报数', nameGap: 22, axisLabel: commonText, splitLine: { lineStyle: { color: '#dfe7f1' } } },
      { type: 'value', name: '万元', nameGap: 22, axisLabel: commonText, splitLine: { show: false } }
    ],
    series: [
      {
        name: '提报数',
        type: 'line',
        smooth: true,
        data: summary.trend.counts,
        symbolSize: 8,
        symbol: 'circle',
        lineStyle: { width: 3, color: '#5570c6' },
        itemStyle: { color: '#5570c6' }
      },
      {
        name: '预计费用',
        type: 'bar',
        yAxisIndex: 1,
        data: summary.trend.costs,
        barMaxWidth: 44,
        barCategoryGap: '45%',
        itemStyle: { color: '#12a182', borderRadius: [5, 5, 0, 0] }
      }
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
    const [projectAnalytics, summary] = await Promise.all([
      getProjectAnalytics(currentQuery()),
      getDeliverySummary()
    ])
    analytics.value = projectAnalytics
    deliverySummary.value = summary
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
  await downloadReport('/reports/delivery-summary.xlsx', '试运行验收摘要.xlsx')
}

async function downloadAcceptanceWord() {
  await downloadReport('/reports/delivery-summary.docx', '试运行验收摘要.docx')
}

function resizeCharts() {
  statusChart?.resize()
  measureChart?.resize()
  heatmapChart?.resize()
  trendChart?.resize()
}

watch([measureFilter, statusFilter, blockFilter, dateRange], () => {
  void syncQuery()
})

useProjectDataChanged(loadDashboard)

onMounted(async () => {
  statusFilter.value = typeof route.query.status === 'string' ? (route.query.status as ProjectPoolStatus) : ''
  measureFilter.value = typeof route.query.measure_type === 'string' ? route.query.measure_type : ''
  blockFilter.value = typeof route.query.block_name === 'string' ? route.query.block_name : ''
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
