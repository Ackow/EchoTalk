// 路由配置：AppShell 承载侧边栏布局，子路由对应设计稿 14.2 的模块页面。
import { createRouter, createWebHashHistory } from 'vue-router'
import { clearSession, session } from '../auth/session'
import { currentUser } from '../api/auth'
import { beginLoading, endLoading } from '../app/loading'
import AppShell from '../layouts/AppShell.vue'

// 未接入后端的模块统一指向规划中占位页，标题与描述写在路由元信息里。
const module = (path, name, title, desc) => ({
  path,
  name,
  component: () => import('../views/ModulePlaceholder.vue'),
  meta: { title, desc, loadText: '正在加载页面' }
})

const router = createRouter({
  history: createWebHashHistory(), // 使用 hash 模式，兼容 Electron file:// 加载
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { title: '登录', loadText: '正在返回登录' } }, // 登录页独立全屏布局（不在 AppShell 内）
    {
      path: '/',
      component: AppShell, // 应用壳：侧边栏 + 标题栏
      children: [
        { path: '', name: 'workspace', component: () => import('../views/Workspace.vue'), meta: { title: '今日训练', loadText: '正在准备今日训练' } },
        { path: 'practice', name: 'practice', component: () => import('../views/Practice.vue'), meta: { title: '语音对话', loadText: '正在准备练习场景' } }, // 一期文字轮次 + TTS 播报，录音转写后续接入
        { path: 'listening', name: 'listening', component: () => import('../views/ListeningStudio.vue'), meta: { title: '听力工作室', loadText: '正在准备听力工作室' } },
        { path: 'cet', name: 'cet', redirect: { name: 'listening', query: { channel: 'cet' } } },
        { path: 'debate', name: 'debate', component: () => import('../views/Debate.vue'), meta: { title: '多角色对话', loadText: '正在准备多角色对话' } },
        { path: 'debate/create', name: 'debate-create', component: () => import('../views/DebateEditor.vue'), meta: { title: '新建多角色场景', loadText: '正在准备多角色编辑器' } },
        { path: 'debate/:id/edit', name: 'debate-edit', component: () => import('../views/DebateEditor.vue'), meta: { title: '编辑多角色场景', loadText: '正在打开多角色场景' } },
        { path: 'scenes', name: 'scenes', component: () => import('../views/Scenes.vue'), meta: { title: '场景探索', loadText: '正在加载场景' } },
        { path: 'scenes/create', name: 'scene-create', component: () => import('../views/SceneEditor.vue'), meta: { title: '新建场景', loadText: '正在准备场景编辑器' } },
        { path: 'scenes/:id/edit', name: 'scene-edit', component: () => import('../views/SceneEditor.vue'), meta: { title: '编辑场景', loadText: '正在打开场景' } },
        { path: 'knowledge', name: 'knowledge', component: () => import('../views/Knowledge.vue'), meta: { title: '知识工作区', loadText: '正在准备知识工作区' } }, // 一期：场景资料管理；检索随阶段三开放
        { path: 'avatar', name: 'avatar', component: () => import('../views/AvatarSettings.vue'), meta: { title: '数字人角色', loadText: '正在加载角色设置' } }, // 游客可浏览试玩，保存偏好需登录（页面内限制）
        { path: 'review', name: 'review', component: () => import('../views/Review.vue'), meta: { title: '复习计划', loadText: '正在准备复习计划' } },
        { path: 'history', name: 'history', component: () => import('../views/History.vue'), meta: { title: '历史记录', loadText: '正在加载历史记录' } },
        { path: 'analytics', name: 'analytics', component: () => import('../views/Analytics.vue'), meta: { title: '成长分析', loadText: '正在加载成长分析' } },
        { path: 'subscription', name: 'subscription', component: () => import('../views/Subscription.vue'), meta: { title: '任务与积分', loadText: '正在加载任务与积分中心' } }
      ]
    }
  ]
})

// 页面切换前恢复登录身份；游客可直接浏览所有页面，不强制先登录。
// onNavStart/onNavEnd 成对管理全局遮罩：重定向或取消时不触发 afterEach，靠标记补偿避免遮罩卡住。
let navPending = false
router.beforeEach(async (to) => {
  if (navPending) {
    navPending = false
    endLoading()
  }
  navPending = true
  beginLoading(to.meta.loadText || '') // 文案随路由切换：遮罩上显示即将进入的页面在做什么
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

router.afterEach(() => {
  if (!navPending) return
  navPending = false
  endLoading()
})
router.onError(() => {
  if (!navPending) return
  navPending = false
  endLoading()
})

export default router
