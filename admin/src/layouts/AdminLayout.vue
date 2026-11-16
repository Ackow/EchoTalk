<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import brandLogo from '../assets/echotalk-brand.png'
import { adminSession, clearAdminSession } from '../auth/session'
import { logoutAdmin } from '../api/admin'

const route = useRoute()
const router = useRouter()
const collapsed = ref(false)

const menuGroups = [
  { type: 'item', path: '/dashboard', title: '数据概览', icon: 'DataBoard' },
  { type: 'item', path: '/users', title: '用户管理', icon: 'User' },
  {
    type: 'group',
    index: 'group-content',
    title: '内容资源',
    icon: 'Collection',
    children: [
      { path: '/avatars', title: '数字人管理', icon: 'Avatar' },
      { path: '/scenes', title: '1v1 场景管理', icon: 'Collection' },
      { path: '/debates', title: '多角色场景', icon: 'ChatLineSquare' },
      { path: '/listening', title: '听力资源', icon: 'Headset' },
      { path: '/knowledge', title: '知识库管理', icon: 'Files' },
    ],
  },
  {
    type: 'group',
    index: 'group-records',
    title: '训练与数据',
    icon: 'ChatDotRound',
    children: [
      { path: '/sessions', title: '对话记录', icon: 'ChatDotRound' },
      { path: '/reviews', title: '复习与听力记录', icon: 'Reading' },
    ],
  },
  {
    type: 'group',
    index: 'group-saas',
    title: '商业化与运营',
    icon: 'SetUp',
    children: [
      { path: '/saas/plans', title: 'SaaS 套餐配额', icon: 'SetUp' },
      { path: '/saas/tasks', title: '积分任务与活动', icon: 'Trophy' },
      { path: '/saas/orders', title: '订单与兑换码', icon: 'Ticket' },
      { path: '/tokens', title: '盈利与 Token 统计', icon: 'TrendCharts' },
    ],
  },
]

const defaultOpeneds = ['group-content', 'group-records', 'group-saas']
const activePath = computed(() => route.path)
const pageTitle = computed(() => route.meta?.title || 'EchoTalk 管理端')
const activeGroupTitle = computed(() => {
  for (const entry of menuGroups) {
    if (entry.type === 'group' && entry.children.some((c) => c.path === route.path)) {
      return entry.title
    }
  }
  return ''
})

async function handleLogout() {
  try {
    await logoutAdmin()
  } catch {
    // 忽略撤销失败
  } finally {
    clearAdminSession()
    ElMessage.success('已退出登录')
    router.replace('/login')
  }
}
</script>

<template>
  <el-container class="admin-shell">
    <el-aside :width="collapsed ? '64px' : '220px'" class="admin-aside">
      <div class="brand">
        <img :src="brandLogo" alt="EchoTalk" class="brand-logo-img" />
        <span v-if="!collapsed" class="brand-name">EchoTalk Admin</span>
      </div>
      <el-menu
        :default-active="activePath"
        :default-openeds="defaultOpeneds"
        :collapse="collapsed"
        background-color="#0f172a"
        text-color="#cbd5e1"
        active-text-color="#ffffff"
        router
        class="aside-menu"
      >
        <template v-for="entry in menuGroups" :key="entry.index || entry.path">
          <el-menu-item v-if="entry.type === 'item'" :index="entry.path">
            <el-icon><component :is="entry.icon" /></el-icon>
            <template #title>{{ entry.title }}</template>
          </el-menu-item>
          <el-sub-menu v-else :index="entry.index">
            <template #title>
              <el-icon><component :is="entry.icon" /></el-icon>
              <span>{{ entry.title }}</span>
            </template>
            <el-menu-item v-for="sub in entry.children" :key="sub.path" :index="sub.path">
              <el-icon><component :is="sub.icon" /></el-icon>
              <template #title>{{ sub.title }}</template>
            </el-menu-item>
          </el-sub-menu>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="header-left">
          <el-button text @click="collapsed = !collapsed">
            <el-icon size="18">
              <Fold v-if="!collapsed" />
              <Expand v-else />
            </el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">管理端</el-breadcrumb-item>
            <el-breadcrumb-item v-if="activeGroupTitle">{{ activeGroupTitle }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag type="success" effect="plain" size="small">管理员</el-tag>
          <el-dropdown>
            <span class="user-trigger">
              <el-avatar :size="28">{{ adminSession.user?.username?.[0]?.toUpperCase() || 'A' }}</el-avatar>
              <span>{{ adminSession.user?.username || 'Admin' }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-shell {
  height: 100vh;
}

.admin-aside {
  background-color: #0f172a;
  transition: width 0.2s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.brand {
  height: 58px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  color: #ffffff;
  font-weight: 600;
  font-size: 15px;
  white-space: nowrap;
}

.brand-logo-img {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
}

.aside-menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
}

.aside-menu :deep(.el-menu-item.is-active) {
  background-color: #2563eb !important;
  border-radius: 8px;
  margin: 4px 8px;
  width: calc(100% - 16px);
}

.aside-menu :deep(.el-menu-item),
.aside-menu :deep(.el-sub-menu__title) {
  margin: 4px 8px;
  border-radius: 8px;
  height: 42px;
}

.aside-menu :deep(.el-sub-menu .el-menu-item) {
  height: 38px;
  font-size: 13px;
}

.admin-header {
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 58px;
}

.header-left,
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #334155;
}

.admin-main {
  padding: 20px;
  overflow-y: auto;
}
</style>
