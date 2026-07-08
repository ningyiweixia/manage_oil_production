import { http, unwrap } from './http'
import type { PageResult } from '../types/workover'

export type MaterialRequirementStatus = 'PENDING' | 'APPROVED' | 'PLANNED' | 'DELIVERED' | 'ARRIVED' | 'USED' | 'CANCELED'
export type MaterialRequirementType = 'NORMAL' | 'EMERGENCY'

export interface MaterialRequirement {
  id: number
  well_no: string
  operation_sheet_id?: number | null
  material_name: string
  specification?: string | null
  quantity: number
  unit: string
  requirement_type: MaterialRequirementType
  status: MaterialRequirementStatus
  planned_at?: string | null
  delivered_at?: string | null
  arrived_at?: string | null
  used_at?: string | null
  remark?: string | null
  created_at: string
  updated_at: string
}

export interface MaterialRequirementQuery {
  page?: number
  page_size?: number
  well_no?: string
  operation_sheet_id?: number
  status?: MaterialRequirementStatus | ''
  material_name?: string
  requirement_type?: MaterialRequirementType | ''
}

export interface MaterialRequirementPayload {
  well_no: string
  operation_sheet_id?: number | null
  material_name: string
  specification?: string
  quantity: number
  unit: string
  requirement_type: MaterialRequirementType
  remark?: string
}

export interface MaterialAnalytics {
  total: number
  pending: number
  approved: number
  planned: number
  delivered: number
  arrived: number
  used: number
  canceled: number
  emergency_count: number
}

export function listMaterialRequirements(query: MaterialRequirementQuery) {
  const params = Object.fromEntries(Object.entries(query).filter(([, value]) => value !== '' && value !== undefined && value !== null))
  return unwrap<PageResult<MaterialRequirement>>(http.get('/materials/', { params }))
}

export function createMaterialRequirement(payload: MaterialRequirementPayload) {
  return unwrap<MaterialRequirement>(http.post('/materials/', payload))
}

export function updateMaterialRequirement(id: number, payload: Partial<MaterialRequirementPayload> & { status?: MaterialRequirementStatus }) {
  return unwrap<MaterialRequirement>(http.put(`/materials/${id}`, payload))
}

export function deleteMaterialRequirement(id: number) {
  return unwrap<null>(http.delete(`/materials/${id}`))
}

export function getMaterialAnalytics(wellNo?: string) {
  return unwrap<MaterialAnalytics>(http.get('/materials/analytics/summary', { params: wellNo ? { well_no: wellNo } : undefined }))
}
