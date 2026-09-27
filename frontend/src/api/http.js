// 统一 API 客户端：Base URL、令牌自动附加、错误规范化、5xx 幂等重试。
import axios from 'axios'
import { clearSession, session } from '../auth/session'

// 后端地址解析顺序：Electron 注入 → Vite 环境变量 → 本地默认。
const baseUrl = window.electronAPI?.backendBaseUrl || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
export { baseUrl } // 封面等静态资源直链需要拼后端地址

export const http = axios.create({
  baseURL: `${baseUrl}/api`, // 所有请求统一走 /api 前缀
  timeout: 15000 // 15 秒超时，避免请求无限挂起
})

// 请求拦截：登录后自动为每个请求附加 Bearer 令牌。
http.interceptors.request.use((config) => {
  if (session.token) config.headers.Authorization = `Bearer ${session.token}`
  return config
})

// 把各类失败统一转换为带可读 message 的 Error，组件里直接展示 err.message。
function toFriendlyError(error) {
  if (!error.response) {
    return new Error('无法连接服务器，请检查网络或后端是否启动。') // 网络层失败：离线提示
  }
  const body = error.response.data || {}
  const detail = body.error?.message || body.detail
  const fallback = { 401: '登录已失效，请重新登录', 403: '没有执行此操作的权限', 404: '请求的资源不存在', 500: '服务内部错误，请稍后重试' }
  const friendly = new Error(detail || fallback[error.response.status] || `请求失败（${error.response.status}）`)
  friendly.code = body.error?.code // 机器可读错误码：供调用方程序化判断（如导入冲突）
  friendly.details = body.error?.details // 字段级详情：供表单逐项标注
  return friendly
}

// 响应拦截：4xx 不重试直接规范化；网络错误/5xx 仅对幂等的 GET 自动重试（最多 3 次）。
http.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) clearSession() // 会话失效：清除本地登录态，路由守卫将跳转登录页
    const config = error.config || {}
    const retryable = !error.response || error.response.status >= 500 // 网络错误或服务端错误才可重试
    const idempotent = (config.method || 'get') === 'get' // 仅幂等请求自动重试
    config.__retryCount = config.__retryCount || 0
    if (retryable && idempotent && config.__retryCount < 3) {
      config.__retryCount += 1
      await new Promise((resolve) => setTimeout(resolve, 500 * config.__retryCount)) // 递增退避：0.5s/1s/1.5s
      return http.request(config)
    }
    return Promise.reject(toFriendlyError(error))
  }
)
