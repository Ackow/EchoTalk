<template>
  <!-- 布局由路由结构决定：/login 全屏，其余路由在 AppShell 壳层内渲染。 -->
  <router-view />
  <!-- 全局加载遮罩：路由切换、长流程加载时覆盖整个窗口 -->
  <AppLoading />

  <Teleport to="body">
    <div v-if="updateInfo" class="app-update-toast" role="status">
      <div class="update-copy">
        <strong>发现新版本 v{{ updateInfo.latestVersion }}</strong>
        <span>当前版本 v{{ updateInfo.currentVersion }}，点击前往下载最新安装包</span>
      </div>
      <div class="update-actions">
        <button type="button" class="update-btn-ghost" @click="updateInfo = null">稍后</button>
        <button type="button" class="update-btn-primary" @click="openUpdate">前往下载</button>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import AppLoading from './components/AppLoading.vue'

const updateInfo = ref(null)
let stopListening = null

function openUpdate() {
  const url = updateInfo.value?.downloadUrl || updateInfo.value?.releaseUrl
  if (!url) return
  if (window.electronAPI?.openExternal) window.electronAPI.openExternal(url)
  else window.open(url, '_blank')
  updateInfo.value = null
}

onMounted(() => {
  if (window.electronAPI?.onUpdateAvailable) {
    stopListening = window.electronAPI.onUpdateAvailable((info) => {
      updateInfo.value = info
    })
  }
})

onBeforeUnmount(() => {
  if (stopListening) stopListening()
})
</script>

<style scoped>
.app-update-toast {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 16px;
  background: #ffffff;
  border: 1.5px solid #ebe7f5;
  border-bottom: 4px solid #e3dcf2;
  border-radius: 14px;
  box-shadow: 0 12px 28px rgba(41, 40, 62, 0.14);
}
.update-copy { display: flex; flex-direction: column; gap: 2px; }
.update-copy strong { font-size: 13.5px; color: #35304e; }
.update-copy span { font-size: 12px; color: #625e76; }
.update-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
.update-btn-primary {
  padding: 6px 12px;
  border: 1.5px solid #8067d1;
  border-bottom: 3px solid #6951b8;
  border-radius: 9px;
  background: #8b73dd;
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
}
.update-btn-ghost {
  padding: 6px 10px;
  border: 1px solid #e6e1f2;
  border-radius: 9px;
  background: #faf9fd;
  color: #625e76;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
</style>
