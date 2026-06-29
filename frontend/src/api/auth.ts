import { http, unwrap } from './http'

interface LoginPayload {
  username: string
  password: string
}

export interface MenuNode {
  id: number
  title: string
  route_name: string
  route_path: string
  component: string | null
  icon: string | null
  parent_id: number | null
  sort_order: number
  is_visible: boolean
  is_active: boolean
  meta: Record<string, unknown>
  children: MenuNode[]
}

export interface LoginResponse {
  token: {
    access_token: string
    refresh_token: string
    token_type: string
  }
  user: {
    id: number
    username: string
    full_name: string
    department?: string
  }
  permissions: string[]
  menus: MenuNode[]
}

export interface CurrentUser {
  id: number
  username: string
  full_name: string
  department?: string | null
  roles: Array<{ id: number; name: string; code: string }>
  permissions: Array<{ id: number; name: string; code: string }>
  menus: MenuNode[]
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  return unwrap<LoginResponse>(http.post('/auth/login', payload))
}

export async function getCurrentUser(): Promise<CurrentUser> {
  return unwrap<CurrentUser>(http.get('/auth/me'))
}

export async function changeCurrentPassword(payload: { old_password: string; new_password: string }) {
  return unwrap<null>(http.patch('/auth/me/password', payload))
}

export async function cancelCurrentAccount(payload: { password: string }) {
  return unwrap<null>(http.delete('/auth/me', { data: payload }))
}
