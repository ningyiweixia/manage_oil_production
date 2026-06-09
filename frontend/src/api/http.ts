import axios from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '../types/workover'

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 12000
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.dispatchEvent(new CustomEvent('auth-expired'))
      ElMessage.error('登录已失效，请重新登录')
    }
    return Promise.reject(error)
  }
)

export async function unwrap<T>(request: Promise<{ data: ApiResponse<T> }>): Promise<T> {
  const response = await request
  if (response.data.code !== 20000) {
    throw new Error(response.data.msg || '接口返回异常')
  }
  return response.data.data
}
