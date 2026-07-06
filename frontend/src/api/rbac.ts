import { http, unwrap } from './http'
import type { PageResult } from '../types/workover'

export interface UserItem {
  id: number
  username: string
  full_name: string
  department?: string | null
  mobile?: string | null
  email?: string | null
  is_active: boolean
  is_superuser: boolean
  role_ids: number[]
  created_at: string
}

export interface RoleItem {
  id: number
  name: string
  code: string
  description?: string | null
  is_active: boolean
  menu_ids: number[]
  permission_ids: number[]
}

export interface PermissionItem {
  id: number
  name: string
  code: string
  path: string
  method: string
  description?: string | null
  is_active: boolean
}

export interface MenuItem {
  id: number
  parent_id?: number | null
  title: string
  route_name: string
  route_path: string
  component?: string | null
  icon?: string | null
  sort_order: number
  is_visible: boolean
  is_active: boolean
  meta: Record<string, unknown>
  children?: MenuItem[]
}

export interface OperationLogItem {
  id: number
  user_id?: number | null
  username?: string | null
  ip_address?: string | null
  method: string
  path: string
  operation?: string | null
  status_code?: number | null
  response_message?: string | null
  created_at: string
}

export function listUsers() {
  return unwrap<UserItem[]>(http.get('/users'))
}

export function createUser(payload: {
  username: string
  password: string
  full_name: string
  department?: string
  mobile?: string
  email?: string
  is_active: boolean
  role_ids: number[]
}) {
  return unwrap<UserItem>(http.post('/users', payload))
}

export function setUserActive(id: number, isActive: boolean) {
  return unwrap<UserItem>(http.patch(`/users/${id}/active`, null, { params: { is_active: isActive } }))
}

export function deleteUser(id: number) {
  return unwrap<null>(http.delete(`/users/${id}`))
}

export function assignUserRoles(id: number, roleIds: number[]) {
  return unwrap<UserItem>(http.patch(`/users/${id}/roles`, { ids: roleIds }))
}

export function listRoles() {
  return unwrap<RoleItem[]>(http.get('/roles'))
}

export function listPermissions() {
  return unwrap<PermissionItem[]>(http.get('/permissions'))
}

export function listMenus() {
  return unwrap<MenuItem[]>(http.get('/menus'))
}

export function assignRolePermissions(id: number, permissionIds: number[]) {
  return unwrap<RoleItem>(http.patch(`/roles/${id}/permissions`, { ids: permissionIds }))
}

export function listOperationLogs(query: { page?: number; page_size?: number } = {}) {
  return unwrap<PageResult<OperationLogItem>>(http.get('/operation-logs', { params: query }))
}
