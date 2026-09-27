const { contextBridge, ipcRenderer } = require('electron')

// 将安全的 Electron API 方法暴露给渲染进程 (Vue 前端)
contextBridge.exposeInMainWorld('electronAPI', {
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  backendBaseUrl: ipcRenderer.sendSync('get-backend-base-url'),
  // 后续若有需要调用本地原生的方法可在此继续拓展
})
