import { createRouter, createWebHashHistory } from 'vue-router'
import { adminSession, clearAdminSession } from '../auth/session'
import { fetchCurrentUser } from '../api/admin'
import AdminLayout from '../layouts/AdminLayout.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/Login.vue'),
      meta: { title: '管理员登录' },
    },
    {
      path: '/',
      component: AdminLayout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'dashboard',
          component: () => import('../views/Dashboard.vue'),
          meta: { title: '数据概览', icon: 'DataBoard' },
        },
        {
          path: 'users',
          name: 'users',
          component: () => import('../views/Users.vue'),
          meta: { title: '用户管理', icon: 'User' },
        },
        {
          path: 'avatars',
          name: 'avatars',
          component: () => import('../views/Avatars.vue'),
          meta: { title: '数字人管理', icon: 'Avatar' },
        },
        {
          path: 'scenes',
          name: 'scenes',
          component: () => import('../views/Scenes.vue'),
          meta: { title: '场景管理', icon: 'Collection' },
        },
        {
          path: 'debates',
          name: 'debates',
          component: () => import('../views/DebateTopics.vue'),
          meta: { title: '多角色场景', icon: 'ChatLineSquare' },
        },
        {
          path: 'listening',
          name: 'listening',
          component: () => import('../views/ListeningResources.vue'),
          meta: { title: '听力资源管理', icon: 'Headset' },
        },
        {
          path: 'knowledge',
          name: 'knowledge',
          component: () => import('../views/KnowledgeAdmin.vue'),
          meta: { title: '知识库管理', icon: 'Files' },
        },
        {
          path: 'reviews',
          name: 'reviews',
          component: () => import('../views/ReviewsAdmin.vue'),
          meta: { title: '复习与听力记录', icon: 'Reading' },
        },
        {
          path: 'sessions',
          name: 'sessions',
          component: () => import('../views/Sessions.vue'),
          meta: { title: '对话记录', icon: 'ChatDotRound' },
        },
        {
          path: 'tokens',
          name: 'tokens',
          component: () => import('../views/TokenStats.vue'),
          meta: { title: '盈利与 Token 统计', icon: 'TrendCharts' },
        },
        {
          path: 'saas/plans',
          name: 'saas-plans',
          component: () => import('../views/SaasPlans.vue'),
          meta: { title: 'SaaS 套餐配额', icon: 'SetUp' },
        },
        {
          path: 'saas/tasks',
          name: 'saas-tasks',
          component: () => import('../views/TasksAndCampaigns.vue'),
          meta: { title: '积分任务与活动', icon: 'Trophy' },
        },
        {
          path: 'saas/orders',
          name: 'saas-orders',
          component: () => import('../views/OrdersAndCodes.vue'),
          meta: { title: '订单流水与兑换码', icon: 'Ticket' },
        },
      ],
    },
  ],
})

router.beforeEach(async (to) => {
  if (to.name === 'login') {
    if (adminSession.token && adminSession.user?.is_admin) {
      return { name: 'dashboard' }
    }
    return true
  }

  if (!adminSession.token) {
    return { name: 'login' }
  }

  if (!adminSession.user) {
    try {
      const { data } = await fetchCurrentUser()
      if (!data.is_admin) {
        clearAdminSession()
        return { name: 'login' }
      }
      adminSession.user = data
    } catch {
      clearAdminSession()
      return { name: 'login' }
    }
  }
  return true
})

export default router
