<template>
  <section class="dashboard-filters">
    <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" />
    <el-select v-model="measureFilter" clearable placeholder="措施类别" style="width: 180px">
      <el-option v-for="item in measureTypes" :key="item" :label="item" :value="item" />
    </el-select>
    <el-select v-model="statusFilter" clearable placeholder="审批状态" style="width: 180px">
      <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
    </el-select>
    <el-input v-model="blockFilter" clearable placeholder="区块" style="width: 160px" />
    <el-button type="primary" :icon="Refresh" @click="loadDashboard">刷新</el-button>
    <el-button :icon="Download" @click="exportSummary">导出摘要</el-button>
  </section>

  <section class="kpi-grid">
    <div v-for="item in kpis" :key="item.label" class="kpi-card">
      <span>{{ item.label }}</span>
      <strong>{{ item.value }}</strong>
      <small>{{ item.hint }}</small>
    </div>
  </section>

  <section class="chart-grid">
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
import { demoProjectDataset, listProjects } from '../api/workover'
import { useProjectDataChanged } from '../composables/useProjectSync'
import { statusLabels } from '../utils/status'
import type { ProjectPoolStatus, WorkoverProject } from '../types/workover'

const route = useRoute()
const router = useRouter()
const projects = ref<WorkoverProject[]>([])
const dateRange = ref<[Date, Date] | null>(null)
const measureFilter = ref('')
const statusFilter = ref('')
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

const filteredProjects = computed(() => {
  return projects.value.filter((project) => {
    const matchesMeasure = !measureFilter.value || project.measures_jsonb.measures?.some((item) => item.measure_type === measureFilter.value)
    const matchesStatus = !statusFilter.value || project.status === statusFilter.value
    const matchesBlock = !blockFilter.value || project.block_name?.includes(blockFilter.value)
    const createdAt = new Date(project.created_at)
    const matchesDate = !dateRange.value || (createdAt >= dateRange.value[0] && createdAt <= dateRange.value[1])
    return matchesMeasure && matchesStatus && matchesBlock && matchesDate
  })
})

const measureTypes = computed(() => {
  return Array.from(new Set(projects.value.flatMap((project) => project.measures_jsonb.measures?.map((measure) => measure.measure_type) || [])))
})

const kpis = computed(() => {
  const rows = filteredProjects.value
  const totalCost = rows.reduce((sum, row) => sum + (row.measures_jsonb.measures || []).reduce((inner, item) => inner + Number(item.estimated_cost || 0), 0), 0)
  const approved = rows.filter((row) => row.status === 'APPROVED' || row.status === 'DISPATCHED').length
  const pending = rows.filter((row) => row.status === 'PENDING_GEOLOGY_VERIFY' || row.status === 'PENDING_PROCESS_VERIFY').length
  return [
    { label: '项目池总量', value: rows.length, hint: '当前筛选范围' },
    { label: '待办审批', value: pending, hint: '地质/工艺核实' },
    { label: '通过率', value: rows.length ? `${Math.round((approved / rows.length) * 100)}%` : '0%', hint: '已通过与已派工' },
    { label: '预计费用', value: `${totalCost.toFixed(1)} 万`, hint: '措施费用汇总' }
  ]
})

function aggregateByStatus() {
  return Object.keys(statusLabels).map((status) => filteredProjects.value.filter((project) => project.status === status).length)
}

function aggregateMeasures() {
  const bucket = new Map<string, number>()
  filteredProjects.value.forEach((project) => {
    project.measures_jsonb.measures?.forEach((measure) => bucket.set(measure.measure_type, (bucket.get(measure.measure_type) || 0) + 1))
  })
  return Array.from(bucket.entries()).map(([name, value]) => ({ name, value }))
}

function heatmapData() {
  const blocks = Array.from(new Set(filteredProjects.value.map((project) => project.block_name || '未填区块')))
  const statuses = ['PENDING_GEOLOGY_VERIFY', 'PENDING_PROCESS_VERIFY', 'APPROVED', 'REJECTED'] as ProjectPoolStatus[]
  const data: [number, number, number][] = []
  blocks.forEach((block, x) => {
    statuses.forEach((status, y) => {
      const priority = filteredProjects.value
        .filter((project) => (project.block_name || '未填区块') === block && project.status === status)
        .reduce((sum, project) => sum + project.production_priority, 0)
      data.push([x, y, priority])
    })
  })
  return { blocks, statuses, data }
}

function trendData() {
  const bucket = new Map<string, { count: number; cost: number }>()
  filteredProjects.value.forEach((project) => {
    const day = project.created_at.slice(5, 10)
    const cost = (project.measures_jsonb.measures || []).reduce((sum, measure) => sum + Number(measure.estimated_cost || 0), 0)
    const current = bucket.get(day) || { count: 0, cost: 0 }
    bucket.set(day, { count: current.count + 1, cost: current.cost + cost })
  })
  const days = Array.from(bucket.keys()).sort()
  return { days, counts: days.map((day) => bucket.get(day)?.count || 0), costs: days.map((day) => bucket.get(day)?.cost || 0) }
}

function renderCharts() {
  const heatmap = heatmapData()
  const trend = trendData()
  const commonText = { color: '#2b3445', fontFamily: 'Microsoft YaHei, Arial' }

  statusChart?.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 24, top: 28, bottom: 40 },
    xAxis: { type: 'category', data: Object.values(statusLabels), axisLabel: commonText },
    yAxis: { type: 'value', axisLabel: commonText },
    series: [{ type: 'bar', data: aggregateByStatus(), barWidth: 32, itemStyle: { color: '#2f7de1', borderRadius: [4, 4, 0, 0] } }]
  } satisfies EChartsOption)

  measureChart?.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: commonText },
    series: [{ type: 'pie', radius: ['42%', '68%'], center: ['50%', '45%'], data: aggregateMeasures(), label: { formatter: '{b}: {d}%' } }]
  } satisfies EChartsOption)

  heatmapChart?.setOption({
    tooltip: { position: 'top' },
    grid: { left: 70, right: 24, top: 24, bottom: 50 },
    xAxis: { type: 'category', data: heatmap.blocks, axisLabel: commonText },
    yAxis: { type: 'category', data: heatmap.statuses.map((status) => statusLabels[status]), axisLabel: commonText },
    visualMap: { min: 0, max: 200, calculable: true, orient: 'horizontal', left: 'center', bottom: 0 },
    series: [{ type: 'heatmap', data: heatmap.data, label: { show: true } }]
  } satisfies EChartsOption)

  trendChart?.setOption({
    tooltip: { trigger: 'axis' },
    legend: { top: 0, textStyle: commonText },
    grid: { left: 46, right: 46, top: 42, bottom: 42 },
    xAxis: { type: 'category', data: trend.days, axisLabel: commonText },
    yAxis: [
      { type: 'value', name: '提报数', axisLabel: commonText },
      { type: 'value', name: '万元', axisLabel: commonText }
    ],
    series: [
      { name: '提报数', type: 'line', smooth: true, data: trend.counts, symbolSize: 8 },
      { name: '预计费用', type: 'bar', yAxisIndex: 1, data: trend.costs, itemStyle: { color: '#12a182', borderRadius: [4, 4, 0, 0] } }
    ]
  } satisfies EChartsOption)
}

async function loadDashboard() {
  const result = await listProjects({ page: 1, page_size: 200 })
  projects.value = result.items.length ? result.items : demoProjectDataset()
  await nextTick()
  renderCharts()
}

function syncQuery() {
  router.replace({
    path: '/dashboard',
    query: {
      status: statusFilter.value || undefined,
      measure_type: measureFilter.value || undefined,
      block_name: blockFilter.value || undefined
    }
  })
  renderCharts()
}

function saveChart(chart: ECharts | null, name: string) {
  if (!chart) return
  const link = document.createElement('a')
  link.href = chart.getDataURL({ pixelRatio: 2, backgroundColor: '#ffffff' })
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
  URL.revokeObjectURL(link.href)
  ElMessage.success('摘要已导出')
}

function resizeCharts() {
  statusChart?.resize()
  measureChart?.resize()
  heatmapChart?.resize()
  trendChart?.resize()
}

watch([measureFilter, statusFilter, blockFilter], syncQuery)
useProjectDataChanged(loadDashboard)

onMounted(async () => {
  statusFilter.value = typeof route.query.status === 'string' ? route.query.status : ''
  measureFilter.value = typeof route.query.measure_type === 'string' ? route.query.measure_type : ''
  blockFilter.value = typeof route.query.block_name === 'string' ? route.query.block_name : ''
  statusChart = echarts.init(statusChartRef.value!)
  measureChart = echarts.init(measureChartRef.value!)
  heatmapChart = echarts.init(heatmapChartRef.value!)
  trendChart = echarts.init(trendChartRef.value!)
  window.addEventListener('resize', resizeCharts)
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
