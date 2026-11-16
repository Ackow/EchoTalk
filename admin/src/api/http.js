import axios from 'axios'
import { ElMessage } from 'element-plus'
import { adminSession, clearAdminSession } from '../auth/session'

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')

export function apiUrl(path) {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalized}`
}

export const http = axios.create({
  baseURL: API_BASE_URL ? `${API_BASE_URL}/api` : '/api',
  timeout: 15000,
})

http.interceptors.request.use((config) => {
  if (adminSession.token) {
    config.headers.Authorization = `Bearer ${adminSession.token}`
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const message = error.response?.data?.error?.message || error.message || '请求失败'

    if (status === 401) {
      clearAdminSession()
      if (!window.location.hash.includes('#/login')) {
        window.location.hash = '#/login'
      }
    }
    ElMessage.error(message)
    return Promise.reject(error)
  }
)
