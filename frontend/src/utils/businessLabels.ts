const measureTypeLabels: Record<string, string> = {
  major_workover: '大修作业',
  pump_repair: '泵修作业',
  pump_inspection: '起泵检查',
  sand_washing: '冲砂作业',
  tubing_replacement: '更换油管',
  casing_damage_treatment: '套损治理',
  acidizing: '酸化作业',
  fracturing: '压裂作业',
  hot_wax_washing: '热洗作业'
}

const capabilityLabels: Record<string, string> = {
  demo: '通用作业能力',
  major_repair: '大修作业能力',
  acidizing: '酸化作业能力',
  fracturing: '压裂作业能力',
  sand_control: '防砂作业能力',
  deep_well: '深井作业能力'
}

const projectSourceLabels: Record<string, string> = {
  manual: '人工录入',
  excel: 'Excel 导入',
  external: '外部系统同步'
}

export function measureTypeLabel(value?: string | null) {
  if (!value) return '-'
  return measureTypeLabels[value] || value
}

export function capabilityLabel(value?: string | null) {
  if (!value) return '-'
  return capabilityLabels[value] || value
}

export function projectSourceLabel(value?: string | null) {
  if (!value) return '-'
  return projectSourceLabels[value] || value
}
