import { createRouter, createWebHashHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/practice/:sceneId',
    name: 'Practice',
    component: () => import('../views/Practice.vue'),
    props: true
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('../views/History.vue')
  }
]

const router = createRouter({
  // 在 Electron 桌面客户端中，推荐使用 Hash 路由模式
  history: createWebHashHistory(),
  routes
})

export default router
