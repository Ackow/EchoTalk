import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'Home', component: () => import('../views/Home.vue') },
  { path: '/features', name: 'Features', component: () => import('../views/Features.vue') },
  { path: '/pricing', name: 'Pricing', component: () => import('../views/Pricing.vue') },
  { path: '/community', name: 'Community', component: () => import('../views/Community.vue') },
  { path: '/docs', name: 'Docs', component: () => import('../views/Docs.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to) {
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth', top: 84 }
    }
    return { top: 0 }
  },
})

export default router
