<template>
  <div class="app-layout">
    <!-- Sidebar Navigation -->
    <aside :class="['sidebar glass-panel', { 'sidebar-hidden': isPracticeMode }]">
      <div class="logo-area">
        <h2 class="text-gradient">EchoTalk</h2>
        <span class="tag">云音口语</span>
      </div>
      
      <nav class="menu-list">
        <router-link to="/" class="menu-item" active-class="active">
          <el-icon><Compass /></el-icon>
          <span>练习场景</span>
        </router-link>
        <router-link to="/history" class="menu-item" active-class="active">
          <el-icon><Clock /></el-icon>
          <span>历史回放</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="version">Version 1.0.0 (MVP)</div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="content-view">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" :key="$route.path" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
const isPracticeMode = computed(() => route.name === 'Practice')
</script>

<style scoped>
.app-layout {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: var(--bg-color);
}

.sidebar {
  width: 260px;
  height: calc(100vh - 32px);
  margin: 16px;
  display: flex;
  flex-direction: column;
  padding: 32px 20px;
  border-radius: 16px;
  z-index: 10;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              margin 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              padding 0.3s cubic-bezier(0.4, 0, 0.2, 1),
              opacity 0.2s ease;
  overflow: hidden;
}

.sidebar-hidden {
  width: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  opacity: 0 !important;
  pointer-events: none;
  border: none !important;
}

.logo-area {
  margin-bottom: 40px;
  text-align: center;
}

.logo-area h2 {
  font-size: 2.2rem;
  font-family: var(--font-display);
  font-weight: 800;
  margin-bottom: 4px;
}

.logo-area .tag {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--text-muted);
  font-weight: 600;
}

.menu-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-grow: 1;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-radius: 10px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.95rem;
  font-weight: 500;
  transition: var(--transition-smooth);
}

.menu-item .el-icon {
  font-size: 1.2rem;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.menu-item.active {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(59, 130, 246, 0.15) 100%);
  border: 1px solid rgba(99, 102, 241, 0.25);
  color: var(--primary-color);
  font-weight: 600;
}

.sidebar-footer {
  text-align: center;
}

.version {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.content-view {
  flex-grow: 1;
  height: 100%;
  overflow: hidden;
  position: relative;
}

/* Page transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
