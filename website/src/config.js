// 后端 API 根地址：
// - 本地开发（npm run dev）留空，由 vite.config.js 将 /api 代理到 http://127.0.0.1:8000
// - Cloudflare Pages 生产构建：在 Pages 环境变量中配置 VITE_API_BASE_URL（如 https://api.your-domain.com）
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '')

export function apiUrl(path) {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalized}`
}
