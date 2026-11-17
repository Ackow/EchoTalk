// 预加载脚本：以受控方式向渲染进程暴露必要的 Electron 能力。
const { contextBridge, ipcRenderer } = require('electron')

// 将安全的 Electron API 方法暴露给渲染进程 (Vue 前端)
contextBridge.exposeInMainWorld('electronAPI', {
  getAppVersion: () => ipcRenderer.invoke('get-app-version'), // 异步获取应用版本
  getCurrentReleaseNotes: () => ipcRenderer.invoke('get-current-release-notes'),
  checkForUpdates: () => ipcRenderer.invoke('check-for-updates'), // 检查 GitHub Releases 新版本
  openExternal: (url) => ipcRenderer.invoke('open-external', url), // 用系统浏览器打开链接
  onUpdateAvailable: (callback) => {
    if (typeof callback !== 'function') return () => {}
    const handler = (_event, info) => callback(info)
    ipcRenderer.on('update-available', handler)
    return () => ipcRenderer.removeListener('update-available', handler)
  },
  platform: process.platform, // 运行平台：用于 CSS 区分 macOS 红绿灯留白等平台差异
  // 窗口控制按钮由 titleBarOverlay 原生提供，无需在此转发 IPC
})
