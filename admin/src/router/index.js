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
          path: 'sessions',
          name: 'sessions',
          component: () => import('../views/Sessions.vue'),
          meta: { title: '对话记录', icon: 'ChatDotRound' },
        },
        {
          path: 'tokens',
          name: 'tokens',
          component: () => import('../views/TokenStats.vue'),
          meta: { title: 'API Token 统计', icon: 'TrendCharts' },
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
