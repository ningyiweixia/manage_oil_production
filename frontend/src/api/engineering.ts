import { http, unwrap } from './http'
import type { PageResult } from '../types/workover'

export interface EngineeringDesign {
  id: number
  project_id: number | null
  well_no: string
  version: string
  minio_bucket: string
  minio_object_key: string
  checksum?: string | null
  remark?: string | null
  created_at: string
  updated_at: string
}

export interface RuleCheckResult {
  passed: boolean
  errors: string[]
  warnings: string[]
}

export interface DesignGenerateResult {
  design: EngineeringDesign
  rule_check: RuleCheckResult
}

export function listDesigns(query: { page?: number; page_size?: number; well_no?: string; project_id?: number }) {
  return unwrap<PageResult<EngineeringDesign>>(http.get('/engineering-designs/', { params: query }))
}

export function generateDesign(payload: { project_id: number; well_no: string; template_type: 'word' | 'excel' }) {
  return unwrap<DesignGenerateResult>(http.post('/engineering-designs/generate', payload))
}

export function checkDesignRules(projectId: number) {
  return unwrap<RuleCheckResult>(http.post('/engineering-designs/check-rules', null, { params: { project_id: projectId } }))
}

export function getDesignDownloadUrl(id: number) {
  return unwrap<{ download_url: string; expire_seconds: number }>(http.get(`/engineering-designs/${id}/download`))
}

export function deleteDesign(id: number) {
  return unwrap<void>(http.delete(`/engineering-designs/${id}`))
}
