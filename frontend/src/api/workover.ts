import { http, unwrap } from './http'
import type { AnalyticsQuery, PageResult, ProjectPoolStatus, ProjectQuery, WorkoverAnalytics, WorkoverProject } from '../types/workover'
import { statusLabels } from '../utils/status'

const DEMO_PROJECTS_KEY = 'demo_workover_projects'

const initialDemoProjects: WorkoverProject[] = [
  {
    id: 1001,
    well_no: 'CY2-136',
    well_name: '采二-136',
    layer: '长6',
    fault_description: '产液下降，检泵周期缩短',
    territory_unit: '采油一队',
    block_name: '北一区',
    report_unit: '采油一队',
    production_priority: 92,
    status: 'PENDING_GEOLOGY_VERIFY',
    reason: '产量核实后建议优先安排',
    measures_jsonb: { measures: [{ measure_type: '检泵', process: '起泵检查', construction_params: { pump: '44mm' }, duration_days: 3, estimated_cost: 7.8 }] },
    remark: '需关注含砂',
    created_at: '2026-06-01T08:30:00Z',
    updated_at: '2026-06-08T10:12:00Z'
  },
  {
    id: 1002,
    well_no: 'CY2-208',
    well_name: '采二-208',
    layer: '延9',
    fault_description: '油管结蜡，井口回压升高',
    territory_unit: '采油二队',
    block_name: '南二区',
    report_unit: '采油二队',
    production_priority: 78,
    status: 'PENDING_PROCESS_VERIFY',
    reason: '工艺复核待确认',
    measures_jsonb: { measures: [{ measure_type: '热洗清蜡', process: '热洗', construction_params: { temperature: '85C' }, duration_days: 2, estimated_cost: 4.2 }] },
    created_at: '2026-06-02T09:10:00Z',
    updated_at: '2026-06-08T12:20:00Z'
  },
  {
    id: 1003,
    well_no: 'CY2-315',
    well_name: '采二-315',
    layer: '长8',
    fault_description: '套损疑似，需小修验证',
    territory_unit: '采油三队',
    block_name: '东三块',
    report_unit: '采油三队',
    production_priority: 88,
    status: 'APPROVED',
    reason: '具备上修条件',
    measures_jsonb: { measures: [{ measure_type: '套损治理', process: '通井探套', construction_params: { depth: 1830 }, duration_days: 5, estimated_cost: 16.5 }] },
    created_at: '2026-06-03T11:20:00Z',
    updated_at: '2026-06-08T15:35:00Z'
  },
  {
    id: 1004,
    well_no: 'CY2-421',
    well_name: '采二-421',
    layer: '延10',
    fault_description: '措施效果递减',
    territory_unit: '采油四队',
    block_name: '西四块',
    report_unit: '采油四队',
    production_priority: 51,
    status: 'REJECTED',
    reason: '资料不足，退回补充',
    measures_jsonb: { measures: [{ measure_type: '酸化', process: '小型酸化', construction_params: { acid: '复合酸' }, duration_days: 4, estimated_cost: 12.3 }] },
    created_at: '2026-06-04T14:00:00Z',
    updated_at: '2026-06-09T08:10:00Z'
  },
  {
    id: 1005,
    well_no: 'CY2-506',
    well_name: '采二-506',
    layer: '长7',
    fault_description: '动液面下降，需复核供液能力',
    territory_unit: '采油五队',
    block_name: '北一区',
    report_unit: '采油五队',
    production_priority: 64,
    status: 'DRAFT',
    reason: '基层新提报，待提交审核',
    measures_jsonb: { measures: [{ measure_type: '冲砂洗井', process: '连续冲砂', construction_params: { fluid: '清水' }, duration_days: 2, estimated_cost: 5.6 }] },
    created_at: '2026-06-05T08:20:00Z',
    updated_at: '2026-06-05T08:20:00Z'
  },
  {
    id: 1006,
    well_no: 'CY2-618',
    well_name: '采二-618',
    layer: '延8',
    fault_description: '泵效下降，电流波动',
    territory_unit: '采油六队',
    block_name: '南二区',
    report_unit: '采油六队',
    production_priority: 83,
    status: 'PENDING_GEOLOGY_VERIFY',
    reason: '需地质核实剩余油潜力',
    measures_jsonb: { measures: [{ measure_type: '检泵', process: '起泵复查', construction_params: { pump: '38mm' }, duration_days: 3, estimated_cost: 8.1 }] },
    created_at: '2026-06-06T09:40:00Z',
    updated_at: '2026-06-07T10:15:00Z'
  },
  {
    id: 1007,
    well_no: 'CY2-733',
    well_name: '采二-733',
    layer: '长6',
    fault_description: '注采对应关系变化，措施效果待评估',
    territory_unit: '采油七队',
    block_name: '东三块',
    report_unit: '采油七队',
    production_priority: 72,
    status: 'PENDING_PROCESS_VERIFY',
    reason: '工艺所确认措施参数',
    measures_jsonb: { measures: [{ measure_type: '酸化', process: '分层酸化', construction_params: { stages: 2 }, duration_days: 4, estimated_cost: 14.8 }] },
    created_at: '2026-06-07T11:00:00Z',
    updated_at: '2026-06-08T09:30:00Z'
  },
  {
    id: 1008,
    well_no: 'CY2-802',
    well_name: '采二-802',
    layer: '延10',
    fault_description: '油管老化，存在更换需求',
    territory_unit: '采油八队',
    block_name: '西四块',
    report_unit: '采油八队',
    production_priority: 69,
    status: 'DISPATCHED',
    reason: '已进入派工执行',
    measures_jsonb: { measures: [{ measure_type: '管柱更换', process: '起下管柱', construction_params: { tubing: '73mm' }, duration_days: 6, estimated_cost: 19.4 }] },
    created_at: '2026-06-08T13:10:00Z',
    updated_at: '2026-06-10T08:45:00Z'
  },
  {
    id: 1009,
    well_no: 'CY2-909',
    well_name: '采二-909',
    layer: '长8',
    fault_description: '历史资料不完整，暂不具备审批条件',
    territory_unit: '采油九队',
    block_name: '北一区',
    report_unit: '采油九队',
    production_priority: 45,
    status: 'VOIDED',
    reason: '重复提报，已作废',
    measures_jsonb: { measures: [{ measure_type: '热洗清蜡', process: '热洗复核', construction_params: { temperature: '80C' }, duration_days: 1, estimated_cost: 3.2 }] },
    created_at: '2026-06-09T15:20:00Z',
    updated_at: '2026-06-09T16:30:00Z'
  }
]

function demoProjects(): WorkoverProject[] {
  const cached = localStorage.getItem(DEMO_PROJECTS_KEY)
  if (!cached) {
    localStorage.setItem(DEMO_PROJECTS_KEY, JSON.stringify(initialDemoProjects))
    return initialDemoProjects
  }
  try {
    const projects = JSON.parse(cached) as WorkoverProject[]
    if (projects.length < initialDemoProjects.length) {
      const existingIds = new Set(projects.map((item) => item.id))
      const merged = [...projects, ...initialDemoProjects.filter((item) => !existingIds.has(item.id))]
      saveDemoProjects(merged)
      return merged
    }
    return projects
  } catch {
    localStorage.setItem(DEMO_PROJECTS_KEY, JSON.stringify(initialDemoProjects))
    return initialDemoProjects
  }
}

function saveDemoProjects(projects: WorkoverProject[]) {
  localStorage.setItem(DEMO_PROJECTS_KEY, JSON.stringify(projects))
}

function filterDemo(query: ProjectQuery): PageResult<WorkoverProject> {
  const page = query.page || 1
  const pageSize = query.page_size || 20
  const items = demoProjects().filter((item) => {
    const matchesStatus = !query.status || item.status === query.status
    const matchesWell = !query.well_no || item.well_no.includes(query.well_no)
    const matchesBlock = !query.block_name || item.block_name?.includes(query.block_name)
    const matchesMeasure = !query.measure_type || item.measures_jsonb.measures?.some((measure) => measure.measure_type.includes(query.measure_type || ''))
    return matchesStatus && matchesWell && matchesBlock && matchesMeasure
  })
  return { items: items.slice((page - 1) * pageSize, page * pageSize), total: items.length, page, page_size: pageSize }
}

function compactQuery<T extends object>(query: T) {
  return Object.fromEntries(
    Object.entries(query).filter(([, value]) => value !== '' && value !== undefined && value !== null)
  )
}

function buildAnalytics(projects: WorkoverProject[], query: AnalyticsQuery = {}): WorkoverAnalytics {
  const filtered = projects.filter((project) => {
    const createdDay = project.created_at.slice(0, 10)
    const matchesStart = !query.start_date || createdDay >= query.start_date
    const matchesEnd = !query.end_date || createdDay <= query.end_date
    const matchesStatus = !query.status || project.status === query.status
    const matchesBlock = !query.block_name || project.block_name?.includes(query.block_name)
    const matchesMeasure = !query.measure_type || project.measures_jsonb.measures?.some((measure) => measure.measure_type.includes(query.measure_type || ''))
    return matchesStart && matchesEnd && matchesStatus && matchesBlock && matchesMeasure
  })
  const statusEntries = Object.entries(statusLabels) as [ProjectPoolStatus, string][]
  const measures = filtered.flatMap((project) => project.measures_jsonb.measures || [])
  const totalCost = measures.reduce((sum, measure) => sum + Number(measure.estimated_cost || 0), 0)
  const approved = filtered.filter((project) => project.status === 'APPROVED' || project.status === 'DISPATCHED').length
  const pending = filtered.filter((project) => project.status === 'PENDING_GEOLOGY_VERIFY' || project.status === 'PENDING_PROCESS_VERIFY').length
  const measureBucket = new Map<string, number>()
  measures.forEach((measure) => measureBucket.set(measure.measure_type, (measureBucket.get(measure.measure_type) || 0) + 1))
  const blocks = Array.from(new Set(filtered.map((project) => project.block_name || '未填区块'))).sort()
  const heatmapStatuses = ['PENDING_GEOLOGY_VERIFY', 'PENDING_PROCESS_VERIFY', 'APPROVED', 'REJECTED'] as ProjectPoolStatus[]
  const heatmapData: [number, number, number][] = []
  blocks.forEach((block, x) => {
    heatmapStatuses.forEach((status, y) => {
      const value = filtered
        .filter((project) => (project.block_name || '未填区块') === block && project.status === status)
        .reduce((sum, project) => sum + project.production_priority, 0)
      heatmapData.push([x, y, value])
    })
  })
  const trendBucket = new Map<string, { count: number; cost: number }>()
  filtered.forEach((project) => {
    const day = project.created_at.slice(5, 10)
    const cost = (project.measures_jsonb.measures || []).reduce((sum, measure) => sum + Number(measure.estimated_cost || 0), 0)
    const current = trendBucket.get(day) || { count: 0, cost: 0 }
    trendBucket.set(day, { count: current.count + 1, cost: current.cost + cost })
  })
  const days = Array.from(trendBucket.keys()).sort()
  return {
    kpis: {
      total_projects: filtered.length,
      pending_approvals: pending,
      approval_rate: filtered.length ? Math.round((approved / filtered.length) * 10000) / 100 : 0,
      estimated_cost: Math.round(totalCost * 100) / 100,
      average_priority: filtered.length ? Math.round((filtered.reduce((sum, project) => sum + project.production_priority, 0) / filtered.length) * 100) / 100 : 0
    },
    status_counts: statusEntries.map(([status, label]) => ({ status, label, count: filtered.filter((project) => project.status === status).length })),
    measure_distribution: Array.from(measureBucket.entries()).map(([name, value]) => ({ name, value })),
    heatmap: { blocks, statuses: heatmapStatuses, data: heatmapData },
    trend: {
      days,
      counts: days.map((day) => trendBucket.get(day)?.count || 0),
      costs: days.map((day) => Math.round((trendBucket.get(day)?.cost || 0) * 100) / 100)
    },
    measure_types: Array.from(measureBucket.keys()).sort()
  }
}

export async function listProjects(query: ProjectQuery): Promise<PageResult<WorkoverProject>> {
  return unwrap<PageResult<WorkoverProject>>(http.get('/workover-project-pools/', { params: compactQuery(query) }))
}

export async function getProjectAnalytics(query: AnalyticsQuery): Promise<WorkoverAnalytics> {
  return unwrap<WorkoverAnalytics>(http.get('/workover-project-pools/analytics/summary', { params: compactQuery(query) }))
}

export async function deleteProject(id: number): Promise<void> {
  await unwrap<void>(http.delete(`/workover-project-pools/${id}`))
}

export async function createProject(payload: Omit<WorkoverProject, 'id' | 'created_at' | 'updated_at'>): Promise<WorkoverProject> {
  return unwrap<WorkoverProject>(http.post('/workover-project-pools/', payload))
}

export async function updateProject(id: number, payload: Omit<WorkoverProject, 'id' | 'created_at' | 'updated_at'>): Promise<WorkoverProject> {
  return unwrap<WorkoverProject>(http.put(`/workover-project-pools/${id}`, payload))
}

export async function submitProjects(projectIds: number[], comment: string): Promise<WorkoverProject[]> {
  return unwrap<WorkoverProject[]>(http.patch('/workover-project-pools/submit', { project_ids: projectIds, comment }))
}

export async function patchProjectStatus(id: number, status: ProjectPoolStatus, comment: string): Promise<WorkoverProject> {
  return unwrap<WorkoverProject>(http.patch(`/workover-project-pools/${id}/status`, { status, comment }))
}

export function demoProjectDataset(): WorkoverProject[] {
  return demoProjects()
}

export function demoProjectAnalytics(query: AnalyticsQuery = {}): WorkoverAnalytics {
  return buildAnalytics(demoProjects(), query)
}
