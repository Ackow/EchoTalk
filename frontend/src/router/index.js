// 路由配置：登录页 + 工作区，切换前先恢复服务器确认的登录身份。
import { createRouter, createWebHashHistory } from 'vue-router'
import { clearSession, session } from '../auth/session'
import { currentUser } from '../api/auth'

const router = createRouter({
  history: createWebHashHistory(), // 使用 hash 模式，兼容 Electron file:// 加载
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/Login.vue') }, // 登录/注册页，按需加载
    { path: '/', name: 'workspace', component: () => import('../views/Workspace.vue') } // 工作区主页
  ]
})

// 页面切换前恢复登录身份；游客可直接浏览工作区，不强制先登录。
router.beforeEach(async (to) => {
  if (!session.token) return true // 游客模式：放行所有页面
  if (!session.user) {
    try {
      const { data } = await currentUser() // 有令牌但无用户信息：调 /me 确认身份（令牌由 http.js 自动附加）
      session.user = data
    } catch {
      clearSession() // 令牌已失效：清空登录态
      return to.name === 'login' ? true : { name: 'login' }
    }
  }
  return to.name === 'login' ? { name: 'workspace' } : true // 已登录用户访问登录页时跳回工作区
})

export default router
