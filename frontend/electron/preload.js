// 预加载脚本：以受控方式向渲染进程暴露必要的 Electron 能力。
const { contextBridge, ipcRenderer } = require('electron')

// 将安全的 Electron API 方法暴露给渲染进程 (Vue 前端)
contextBridge.exposeInMainWorld('electronAPI', {
  getAppVersion: () => ipcRenderer.invoke('get-app-version'), // 异步获取应用版本
  platform: process.platform, // 运行平台：用于 CSS 区分 macOS 红绿灯留白等平台差异
  // 窗口控制按钮由 titleBarOverlay 原生提供，无需在此转发 IPC
})
