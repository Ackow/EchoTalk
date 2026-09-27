<template>
  <!-- 工作区主页：侧边栏可整体隐藏；隐藏后按钮融入标题栏（红绿灯右侧，WorkBuddy 式）。 -->
  <main class="workspace-shell" :class="{ 'sidebar-hidden': sidebarHidden }">
    <aside class="sidebar">
      <div class="sidebar-inner">
        <div class="sidebar-traffic"> <!-- macOS 红绿灯落位区（可拖拽移动窗口），展开时折叠按钮靠本行最右侧 -->
          <button
            v-if="!sidebarHidden"
            class="collapse-toggle"
            type="button"
            :aria-pressed="sidebarHidden"
            title="隐藏侧边栏"
            @click="toggleSidebar"
          >
            <AppIcon name="panel" :size="15" />
          </button>
        </div>
        <div class="brand-lockup">
          <span class="brand-mark"><AppIcon name="logo" :size="18" /></span>
          <div class="brand-text"><b>EchoTalk</b><small>2.0 工作区</small></div>
        </div>
        <nav class="side-nav">
          <span class="nav-item active"><AppIcon name="home" :size="15" /><span class="nav-label">工作区</span></span>
        </nav>
        <div class="account-wrap">
          <button
            class="account-trigger"
            type="button"
            :aria-expanded="menuOpen"
            aria-haspopup="menu"
            @click="menuOpen = !menuOpen"
          > <!-- 点击账户卡片弹出上方浮层菜单 -->
            <template v-if="session.user">
              <div class="avatar">{{ session.user?.username?.slice(0, 1)?.toUpperCase() }}</div> <!-- 头像取用户名首字母大写 -->
              <div class="account-name"><b>{{ session.user?.username }}</b></div>
            </template>
            <template v-else>
              <div class="avatar"><AppIcon name="user" :size="15" /></div>
              <div class="account-name"><b>游客</b><small>登录后同步你的数据</small></div>
            </template>
            <AppIcon name="chevron-up" :size="13" class="account-chevron" :class="{ open: menuOpen }" />
          </button>
          <transition name="pop">
            <div v-if="menuOpen" class="account-popover" role="menu">
              <template v-if="session.user">
                <button class="popover-item" type="button" disabled>
                  <AppIcon name="settings" :size="14" />设置
                  <small class="nav-tag">待开发</small>
                </button>
                <div class="popover-divider" aria-hidden="true"></div>
                <button class="popover-item danger" type="button" role="menuitem" @click="handleLogout">
                  <AppIcon name="log-out" :size="14" />退出登录
                </button>
              </template>
              <template v-else>
                <button class="popover-item" type="button" role="menuitem" @click="goLogin">
                  <AppIcon name="user" :size="14" />登录 / 注册
                </button>
              </template>
            </div>
          </transition>
          <div v-if="menuOpen" class="menu-backdrop" @click="menuOpen = false" aria-hidden="true"></div> <!-- 点击菜单外任意区域关闭 -->
        </div>
      </div>
    </aside>
    <section class="workspace-content">
      <header class="content-header"> <!-- 顶栏即拖拽区，双击可最大化；侧栏隐藏时按钮融入此标题栏 -->
        <button
          v-if="sidebarHidden"
          class="collapse-toggle"
          type="button"
          :aria-pressed="sidebarHidden"
          title="显示侧边栏"
          @click="toggleSidebar"
        >
          <AppIcon name="panel" :size="15" />
        </button>
        <h1>工作区</h1>
      </header>
      <div class="empty-state">
        <div class="empty-icon"><AppIcon name="logo" :size="28" /></div>
        <h1>EchoTalk 2.0</h1>
        <p>账户系统已就绪，训练与学习模块即将上线。</p>
        <div class="roadmap" aria-label="后续模块路线">
          <span class="roadmap-chip"><AppIcon name="mic" :size="13" />开口训练</span>
          <span class="roadmap-chip"><AppIcon name="graduation-cap" :size="13" />场景学习</span>
          <span class="roadmap-chip"><AppIcon name="chart-line" :size="13" />复盘分析</span>
        </div>
        <p v-if="error" class="logout-error" role="alert">{{ error }}</p> <!-- 退出失败提示 -->
      </div>
    </section>
  </main>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { logout } from '../api/auth'
import { clearSession, session } from '../auth/session'

const router = useRouter()
const error = ref('') // 退出失败时的错误提示
const menuOpen = ref(false) // 账户浮层菜单开关
const SIDEBAR_PREF_KEY = 'echotalk:sidebar-collapsed' // localStorage 偏好键
const sidebarHidden = ref(localStorage.getItem(SIDEBAR_PREF_KEY) === '1') // 初始状态沿用上次偏好

function toggleSidebar() {
  // 显示/隐藏整个侧边栏，并记住用户偏好。
  sidebarHidden.value = !sidebarHidden.value
  localStorage.setItem(SIDEBAR_PREF_KEY, sidebarHidden.value ? '1' : '0')
}

function handleShortcut(event) {
  // 桌面端惯例：Esc 关闭浮层菜单；Cmd/Ctrl+B 折叠/展开侧边栏。
  if (event.key === 'Escape') menuOpen.value = false
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'b') {
    event.preventDefault()
    toggleSidebar()
  }
}
onMounted(() => window.addEventListener('keydown', handleShortcut))
onBeforeUnmount(() => window.removeEventListener('keydown', handleShortcut))

function goLogin() {
  // 从游客菜单进入登录页。
  menuOpen.value = false
  router.push({ name: 'login' })
}

async function handleLogout() {
  // 后端先撤销令牌；成功后回到登录页切换或重新登录。
  menuOpen.value = false
  error.value = ''
  try {
    await logout() // 令牌由 http.js 自动附加
  } catch (requestError) {
    error.value = requestError.message || '退出服务暂不可用，请检查后端连接后重试。' // 撤销失败保留登录态，让用户重试
    return
  }
  clearSession() // 清空内存与 localStorage
  await router.replace({ name: 'login' })
}
</script>
