import { http, unwrap } from './http'
import type { PageResult, ProjectPoolStatus, ProjectQuery, WorkoverProject } from '../types/workover'

const demoProjects: WorkoverProject[] = [
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
  }
]

function filterDemo(query: ProjectQuery): PageResult<WorkoverProject> {
  const page = query.page || 1
  const pageSize = query.page_size || 20
  const items = demoProjects.filter((item) => {
    const matchesStatus = !query.status || item.status === query.status
    const matchesWell = !query.well_no || item.well_no.includes(query.well_no)
    const matchesBlock = !query.block_name || item.block_name?.includes(query.block_name)
    const matchesMeasure = !query.measure_type || item.measures_jsonb.measures?.some((measure) => measure.measure_type.includes(query.measure_type || ''))
    return matchesStatus && matchesWell && matchesBlock && matchesMeasure
  })
  return { items: items.slice((page - 1) * pageSize, page * pageSize), total: items.length, page, page_size: pageSize }
}

export async function listProjects(query: ProjectQuery): Promise<PageResult<WorkoverProject>> {
  try {
    return await unwrap<PageResult<WorkoverProject>>(http.get('/workover-project-pools/', { params: query }))
  } catch {
    return filterDemo(query)
  }
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
  return demoProjects
}
