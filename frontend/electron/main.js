// Electron 仅承载前端窗口；开发时 FastAPI 由单独终端启动。
const { app, BrowserWindow, ipcMain, shell } = require('electron')
const path = require('path')

function createWindow() {
  const window = new BrowserWindow({
    width: 1280, // 留出品牌区与完整账户工作区
    height: 820,
    minWidth: 900,
    minHeight: 640,
    titleBarStyle: 'hidden', // 隐藏系统标题栏但保留原生窗口能力（边缘缩放、拖拽、双击最大化）
    trafficLightPosition: { x: 16, y: 18 }, // macOS：红绿灯中线 y=24，与标题栏/侧栏顶行 48px 中线对齐
    titleBarOverlay: { color: '#ffffff', symbolColor: '#5e6072', height: 40 }, // Windows/Linux：右上角原生最小化/最大化/关闭按钮；macOS 自动使用左侧红绿灯
    backgroundColor: '#f6f7fb',
    title: 'EchoTalk 2.0',
    autoHideMenuBar: true, // 隐藏默认菜单栏
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'), // 预加载脚本：向渲染进程暴露安全 API
      contextIsolation: true, // 开启上下文隔离，渲染进程无法直接访问 Node
      nodeIntegration: false // 关闭 Node 集成，保证渲染进程安全
    }
  })

  if (app.isPackaged) window.loadFile(path.join(__dirname, '../dist/index.html')) // 打包后加载本地构建产物
  else window.loadURL('http://127.0.0.1:5173') // 开发时加载 Vite 开发服务器

  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url) // 外部 https 链接交给系统浏览器
    return { action: 'deny' } // 应用内一律禁止新开窗口
  })
}

app.whenReady().then(() => {
  ipcMain.handle('get-app-version', () => app.getVersion()) // 渲染进程查询应用版本
  createWindow() // 窗口控制按钮由 titleBarOverlay 原生提供，无需应用内 IPC 转发
  app.on('activate', () => { // macOS 点 Dock 图标时若无窗口则重建
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit() // 非 macOS 关闭全部窗口即退出应用
})
