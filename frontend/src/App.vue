<template>
  <div class="app-layout">
    <!-- Draggable title bar region for frameless window -->
    <div class="electron-drag-bar"></div>

    <!-- ===== Startup Splash Screen ===== -->
    <transition name="splash-fade">
      <div v-if="showSplash" class="splash-overlay">
        <div class="splash-content">
          <!-- Logo Area -->
          <div class="splash-logo-wrap">
            <div class="splash-logo-ring">
              <div class="splash-logo-inner">
                <span class="splash-logo-icon">🎙️</span>
              </div>
            </div>
          </div>

          <!-- App Name -->
          <h1 class="splash-title text-gradient">EchoTalk</h1>
          <p class="splash-subtitle">云音口语</p>

          <!-- Status Area -->
          <div class="splash-status-wrap">
            <!-- First Launch Hint -->
            <div v-if="isFirstLaunch" class="splash-first-launch-hint">
              <span class="hint-icon">✨</span>
              <span>首次启动，正在为您生成场景语音配置，请耐心等待...</span>
            </div>

            <div class="splash-status-row">
              <span class="splash-dot" :class="{ pulsing: !backendReady }"></span>
              <span class="splash-status-text">{{ statusText }}</span>
            </div>

            <!-- Detail text -->
            <div v-if="statusDetail" class="splash-detail-text">{{ statusDetail }}</div>

            <!-- Progress Bar -->
            <div class="splash-progress-track">
              <div class="splash-progress-bar" :style="{ width: progressWidth }"></div>
            </div>

            <!-- Phase Steps -->
            <div class="splash-phase-steps">
              <div class="phase-step" :class="{ done: phaseCompleted('schema'), active: phaseActive('schema') }">
                <span class="step-icon">{{ phaseCompleted('schema') ? '✓' : phaseActive('schema') ? '◉' : '○' }}</span>
                <span>数据库结构</span>
              </div>
              <div class="phase-step" :class="{ done: phaseCompleted('seeding'), active: phaseActive('seeding') }">
                <span class="step-icon">{{ phaseCompleted('seeding') ? '✓' : phaseActive('seeding') ? '◉' : '○' }}</span>
                <span>场景初始化</span>
              </div>
              <div class="phase-step" :class="{ done: phaseCompleted('user'), active: phaseActive('user') }">
                <span class="step-icon">{{ phaseCompleted('user') ? '✓' : phaseActive('user') ? '◉' : '○' }}</span>
                <span>用户注册</span>
              </div>
              <div class="phase-step" :class="{ done: phaseCompleted('done') }">
                <span class="step-icon">{{ phaseCompleted('done') ? '✓' : '○' }}</span>
                <span>就绪</span>
              </div>
            </div>
          </div>

          <!-- Version -->
          <p class="splash-version">Version 1.0.0</p>
        </div>
      </div>
    </transition>

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
        <router-link to="/analytics" class="menu-item" active-class="active">
          <el-icon><TrendCharts /></el-icon>
          <span>成长分析</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <router-link to="/settings" class="menu-item settings-link" active-class="active">
          <el-icon><Setting /></el-icon>
          <span>设置与管理</span>
        </router-link>
        <div class="version" style="margin-top: 12px;">Version 1.0.0 (MVP)</div>
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
import { computed, ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from './store/useAppStore'
import axios from 'axios'

const route = useRoute()
const store = useAppStore()
const isPracticeMode = computed(() => route.name === 'Practice')

// ── Splash state ────────────────────────────────────────────────────────────
const showSplash = ref(false)
const backendReady = ref(false)
const isFirstLaunch = ref(false)
const statusText = ref('正在连接后端服务...')
const statusDetail = ref('')
const progressWidth = ref('0%')
const currentPhase = ref('pending')

// Phase ordering for step indicators
const phaseOrder = ['pending', 'schema', 'seeding', 'user', 'done']

function phaseCompleted(phase) {
  const currentIdx = phaseOrder.indexOf(currentPhase.value)
  const targetIdx = phaseOrder.indexOf(phase)
  return currentIdx > targetIdx
}

function phaseActive(phase) {
  return currentPhase.value === phase
}

// Pre-connection status cycling (before backend is reachable)
const connectingMessages = [
  '正在启动后端服务...',
  '等待服务响应...',
  '连接数据库引擎...',
]
let connectMsgIdx = 0
let connectMsgTimer = null

function cycleConnectMessage() {
  connectMsgIdx = (connectMsgIdx + 1) % connectingMessages.length
  statusText.value = connectingMessages[connectMsgIdx]
}

/**
 * Phase 1: Poll /api/health until backend HTTP server is alive
 * Phase 2: Poll /api/init-status until data initialization is done
 */
async function waitForBackend() {
  const healthUrl = `${store.backendBaseUrl}/api/health`
  const initUrl = `${store.backendBaseUrl}/api/init-status`
  
  // ── Phase 1: Wait for HTTP server to be alive ─────────────────────────
  connectMsgTimer = setInterval(cycleConnectMessage, 2000)
  let serverAlive = false
  let attempts = 0
  const maxConnectAttempts = 120 // 120s to wait for server startup

  while (!serverAlive && attempts < maxConnectAttempts) {
    attempts++
    const pct = Math.min(8, Math.round((attempts / maxConnectAttempts) * 10))
    progressWidth.value = `${pct}%`
    try {
      await axios.get(healthUrl, { timeout: 2000 })
      serverAlive = true
    } catch {
      await sleep(1000)
    }
  }

  if (connectMsgTimer) clearInterval(connectMsgTimer)

  if (!serverAlive) {
    statusText.value = '后端启动超时，请检查安装'
    progressWidth.value = '100%'
    await sleep(2000)
    return
  }

  statusText.value = '后端已连接，正在初始化数据...'
  progressWidth.value = '10%'

  // ── Phase 2: Poll /api/init-status until done ─────────────────────────
  let initDone = false
  let initAttempts = 0
  const maxInitAttempts = 300 // 5min for TTS generation on first launch

  while (!initDone && initAttempts < maxInitAttempts) {
    initAttempts++
    try {
      const res = await axios.get(initUrl, { timeout: 3000 })
      const data = res.data

      // Update UI from real backend status
      currentPhase.value = data.phase || 'pending'
      statusText.value = data.message || '正在初始化...'
      statusDetail.value = data.detail || ''
      isFirstLaunch.value = data.is_first_launch || false

      // Use backend progress but ensure minimum 10% (server is connected)
      const realProgress = Math.max(10, data.progress || 0)
      progressWidth.value = `${realProgress}%`

      if (data.done) {
        initDone = true
        break
      }
    } catch {
      // init-status endpoint not ready yet, keep trying
      statusText.value = '正在等待初始化服务就绪...'
    }
    await sleep(800)
  }

  // Final state
  progressWidth.value = '100%'
  statusText.value = '初始化完成，正在进入应用...'
  statusDetail.value = ''
  backendReady.value = true
  currentPhase.value = 'done'
  await sleep(800)
  store.setAppReady()
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

onMounted(async () => {
  const isElectron = !!window.electronAPI

  if (isElectron) {
    // Electron packaged mode: always show splash, wait for backend to start
    showSplash.value = true
    await waitForBackend()
    showSplash.value = false
  } else {
    // Dev mode: quickly check if init is done, show splash only if needed
    try {
      const res = await axios.get(`${store.backendBaseUrl}/api/init-status`, { timeout: 2000 })
      if (!res.data.done) {
        showSplash.value = true
        await waitForBackend()
        showSplash.value = false
      }
    } catch {
      // Backend likely already running and init is long done, skip splash
    }
  }
  // 覆盖所有分支路径：确保页面组件知道后端已就绪
  store.setAppReady()
})
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
  flex-shrink: 0;
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

.settings-link {
  border: 1px solid rgba(255, 255, 255, 0.04) !important;
  background: rgba(255, 255, 255, 0.02) !important;
  margin-bottom: 8px;
}

.settings-link:hover {
  background: rgba(255, 255, 255, 0.06) !important;
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

/* Electron titlebar drag support */
.electron-drag-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 150px;
  height: 32px;
  -webkit-app-region: drag;
  z-index: 99999;
}

/* Global clickable items insurance policy */
:deep(button), 
:deep(a), 
:deep(.el-button), 
:deep(.el-tabs__item), 
:deep(.el-radio-button),
:deep(.el-input) {
  -webkit-app-region: no-drag;
}

/* ══════════════════════════════════════
   Splash Screen
══════════════════════════════════════ */
.splash-overlay {
  position: fixed;
  inset: 0;
  z-index: 99999;
  background: linear-gradient(135deg, #080c14 0%, #0d1422 40%, #0b1020 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.splash-overlay::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 60% 40% at 50% 30%, rgba(99,102,241,0.12) 0%, transparent 70%),
    radial-gradient(ellipse 40% 50% at 80% 80%, rgba(59,130,246,0.07) 0%, transparent 60%);
  pointer-events: none;
}

.splash-content {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  user-select: none;
}

/* ── Logo ring ────────────────────────── */
.splash-logo-wrap {
  margin-bottom: 28px;
}

.splash-logo-ring {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: conic-gradient(
    from 180deg,
    rgba(99,102,241,0.9) 0%,
    rgba(59,130,246,0.7) 30%,
    rgba(16,185,129,0.4) 60%,
    rgba(99,102,241,0.1) 80%,
    rgba(99,102,241,0.9) 100%
  );
  display: flex;
  align-items: center;
  justify-content: center;
  animation: splash-spin 2.4s linear infinite;
  box-shadow:
    0 0 32px rgba(99,102,241,0.35),
    0 0 64px rgba(99,102,241,0.15);
}

.splash-logo-inner {
  width: 84px;
  height: 84px;
  border-radius: 50%;
  background: #0d1422;
  display: flex;
  align-items: center;
  justify-content: center;
}

.splash-logo-icon {
  font-size: 2.6rem;
  filter: drop-shadow(0 0 12px rgba(99,102,241,0.6));
  animation: splash-pulse 2s ease-in-out infinite;
}

@keyframes splash-spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

@keyframes splash-pulse {
  0%, 100% { transform: scale(1); }
  50%       { transform: scale(1.08); }
}

/* ── Title ────────────────────────────── */
.splash-title {
  font-size: 3.2rem;
  font-family: var(--font-display, 'Inter', sans-serif);
  font-weight: 800;
  letter-spacing: 0.02em;
  margin-bottom: 6px;
  line-height: 1;
}

.splash-subtitle {
  font-size: 1rem;
  color: rgba(148, 163, 184, 0.7);
  letter-spacing: 0.12em;
  margin-bottom: 48px;
  font-weight: 500;
}

/* ── Status ───────────────────────────── */
.splash-status-wrap {
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 32px;
}

.splash-status-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.splash-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6366f1;
  flex-shrink: 0;
  transition: background 0.4s;
}

.splash-dot.pulsing {
  animation: dot-pulse 1.2s ease-in-out infinite;
}

@keyframes dot-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(99,102,241,0.5); }
  50%       { opacity: 0.6; box-shadow: 0 0 0 6px rgba(99,102,241,0); }
}

.splash-status-text {
  font-size: 0.9rem;
  color: rgba(148, 163, 184, 0.85);
  font-weight: 500;
  transition: all 0.4s ease;
}

/* Progress bar */
.splash-progress-track {
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 99px;
  overflow: hidden;
}

.splash-progress-bar {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, #6366f1 0%, #3b82f6 50%, #10b981 100%);
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 0 8px rgba(99,102,241,0.6);
}

/* ── Version ──────────────────────────── */
.splash-version {
  font-size: 0.75rem;
  color: rgba(100, 116, 139, 0.5);
  letter-spacing: 0.1em;
}

/* ── First Launch Hint ───────────────── */
.splash-first-launch-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(99,102,241,0.12) 0%, rgba(16,185,129,0.08) 100%);
  border: 1px solid rgba(99,102,241,0.2);
  font-size: 0.82rem;
  color: rgba(196, 206, 224, 0.9);
  line-height: 1.5;
  animation: hint-fade-in 0.6s ease;
}

.hint-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

@keyframes hint-fade-in {
  from { opacity: 0; transform: translateY(-6px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ── Detail Text ─────────────────────── */
.splash-detail-text {
  font-size: 0.78rem;
  color: rgba(148, 163, 184, 0.5);
  padding-left: 18px;
  transition: all 0.3s ease;
}

/* ── Phase Steps ─────────────────────── */
.splash-phase-steps {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
}

.phase-step {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.72rem;
  color: rgba(100, 116, 139, 0.4);
  transition: all 0.4s ease;
}

.phase-step .step-icon {
  font-size: 0.7rem;
  width: 14px;
  text-align: center;
}

.phase-step.active {
  color: #6366f1;
  font-weight: 600;
}

.phase-step.active .step-icon {
  animation: step-pulse 1.2s ease-in-out infinite;
}

.phase-step.done {
  color: #10b981;
}

@keyframes step-pulse {
  0%, 100% { opacity: 1; }
  50%      { opacity: 0.5; }
}

/* ── Transition ───────────────────────── */
.splash-fade-enter-active {
  transition: opacity 0.3s ease;
}
.splash-fade-leave-active {
  transition: opacity 0.6s ease;
}
.splash-fade-enter-from,
.splash-fade-leave-to {
  opacity: 0;
}
</style>
