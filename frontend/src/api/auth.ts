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

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  return unwrap<LoginResponse>(http.post('/auth/login', payload))
}
