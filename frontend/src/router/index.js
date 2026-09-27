// 路由配置：AppShell 承载侧边栏布局，子路由对应设计稿 14.2 的模块页面。
import { createRouter, createWebHashHistory } from 'vue-router'
import { clearSession, session } from '../auth/session'
import { currentUser } from '../api/auth'
import AppShell from '../layouts/AppShell.vue'

// 未接入后端的模块统一指向规划中占位页，标题与描述写在路由元信息里。
const module = (path, name, title, desc) => ({
  path,
  name,
  component: () => import('../views/ModulePlaceholder.vue'),
  meta: { title, desc }
})

const router = createRouter({
  history: createWebHashHistory(), // 使用 hash 模式，兼容 Electron file:// 加载
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { title: '登录' } }, // 登录页独立全屏布局（不在 AppShell 内）
    {
      path: '/',
      component: AppShell, // 应用壳：侧边栏 + 标题栏
      children: [
        { path: '', name: 'workspace', component: () => import('../views/Workspace.vue'), meta: { title: '今日训练' } },
        module('practice', 'practice', '语音对话', '场景任务对话、录音转写、纠错与流式回复。'),
        module('listening', 'listening', '听力工作室', '精听、听写、跟读与五级辅助训练。'),
        module('cet', 'cet', '四六级训练', 'CET4 / CET6 题型专项与整套模拟。'),
        module('interview', 'interview', '模拟面试', '资料驱动的技术 / HR 追问与课后报告。'),
        module('debate', 'debate', '多角色辩论', '主持、对方与评估角色的回合制辩论。'),
        { path: 'scenes', name: 'scenes', component: () => import('../views/Scenes.vue'), meta: { title: '场景探索' } },
        { path: 'scenes/create', name: 'scene-create', component: () => import('../views/SceneEditor.vue'), meta: { title: '新建场景' } },
        { path: 'scenes/:id/edit', name: 'scene-edit', component: () => import('../views/SceneEditor.vue'), meta: { title: '编辑场景' } },
        module('knowledge', 'knowledge', '知识工作区', '资料上传、解析与带来源的检索问答。'),
        module('avatar', 'avatar', '数字人角色', '角色形象、声音与语速偏好。'),
        module('review', 'review', '复习计划', '听力错题、词汇与表达的复习队列。'),
        module('report', 'report', '训练报告', '课后总结、纠错记录与发音结果。'),
        module('history', 'history', '历史记录', '会话回放与训练记录检索。'),
        module('analytics', 'analytics', '成长分析', '发音雷达、趋势与错因分布。')
      ]
    }
  ]
})

// 页面切换前恢复登录身份；游客可直接浏览所有页面，不强制先登录。
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
