import { http, unwrap } from './http'

interface LoginPayload {
  username: string
  password: string
}

interface LoginResponse {
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
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  return unwrap<LoginResponse>(http.post('/auth/login', payload))
}
