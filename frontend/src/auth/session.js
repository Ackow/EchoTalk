// 全局登录态：跨页面共享的响应式会话对象 + localStorage 持久化。
import { reactive } from 'vue'

export const session = reactive({
  token: localStorage.getItem('echotalk-token'), // 访问令牌：刷新页面后从 localStorage 恢复
  user: null // 当前用户信息：不持久化，由路由守卫调 /me 重新确认
})

// 页面刷新后保留访问令牌；用户资料仍由后端 /me 确认后载入。
export function saveSession(token, user) {
  session.token = token // 更新内存中的令牌
  session.user = user // 更新内存中的用户信息
  localStorage.setItem('echotalk-token', token) // 令牌持久化，刷新后仍保持登录
}

// 清空登录态：内存与 localStorage 一起移除。
export function clearSession() {
  session.token = null
  session.user = null
  localStorage.removeItem('echotalk-token')
}
