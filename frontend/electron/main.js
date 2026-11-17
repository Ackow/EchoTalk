// Electron 仅承载前端窗口；开发时 FastAPI 由单独终端启动。
const { app, BrowserWindow, ipcMain, net, shell } = require('electron')
const path = require('path')
const { extractHighlights } = require('./release-notes')

const GITHUB_RELEASES_API = 'https://api.github.com/repos/Ackow/EchoTalk/releases/latest'
const GITHUB_RELEASES_PAGE = 'https://github.com/Ackow/EchoTalk/releases/latest'

let mainWindow = null

// 注册 echotalk:// 自定义协议，供官网「打开本机 APP」直接唤起桌面端
if (process.defaultApp && process.argv.length >= 2) {
  app.setAsDefaultProtocolClient('echotalk', process.execPath, [path.resolve(process.argv[1])])
} else {
  app.setAsDefaultProtocolClient('echotalk')
}

const gotSingleInstanceLock = app.requestSingleInstanceLock()
if (!gotSingleInstanceLock) {
  app.quit()
}

function focusMainWindow() {
  if (!mainWindow) return
  if (mainWindow.isMinimized()) mainWindow.restore()
  mainWindow.show()
  mainWindow.focus()
}

app.on('second-instance', () => {
  focusMainWindow()
})

app.on('open-url', (event) => {
  event.preventDefault()
  focusMainWindow()
})

function compareVersions(a, b) {
  const pa = String(a || '').replace(/^v/i, '').split('.').map((n) => parseInt(n, 10) || 0)
  const pb = String(b || '').replace(/^v/i, '').split('.').map((n) => parseInt(n, 10) || 0)
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const diff = (pa[i] || 0) - (pb[i] || 0)
    if (diff !== 0) return diff > 0 ? 1 : -1
  }
  return 0
}

function pickInstallerAsset(assets = []) {
  const list = Array.isArray(assets) ? assets : []
  const isMac = process.platform === 'darwin'
  const isWin = process.platform === 'win32'
  const arch = process.arch // arm64 / x64
  if (isMac) {
    return (
      list.find((a) => /\.dmg$/i.test(a.name) && a.name.includes(arch)) ||
      list.find((a) => /\.dmg$/i.test(a.name)) ||
      null
    )
  }
  if (isWin) {
    return (
      list.find((a) => /\.exe$/i.test(a.name) && a.name.includes(arch)) ||
      list.find((a) => /\.exe$/i.test(a.name)) ||
      null
    )
  }
  return null
}

async function checkForUpdates() {
  const currentVersion = app.getVersion()
  try {
    const res = await net.fetch(GITHUB_RELEASES_API, {
      headers: { Accept: 'application/vnd.github+json', 'User-Agent': `EchoTalk/${currentVersion}` },
    })
    if (res.status === 404) {
      return { status: 'latest', currentVersion, latestVersion: currentVersion }
    }
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    const release = await res.json()
    const latestVersion = String(release.tag_name || '').replace(/^v/i, '')
    if (!latestVersion || compareVersions(latestVersion, currentVersion) <= 0) {
      return { status: 'latest', currentVersion, latestVersion: latestVersion || currentVersion }
    }
    const asset = pickInstallerAsset(release.assets)
    return {
      status: 'available',
      currentVersion,
      latestVersion,
      releaseName: release.name || `v${latestVersion}`,
      notes: String(release.body || '').slice(0, 500),
      downloadUrl: asset?.browser_download_url || release.html_url || GITHUB_RELEASES_PAGE,
      releaseUrl: release.html_url || GITHUB_RELEASES_PAGE,
    }
  } catch (err) {
    return {
      status: 'error',
      currentVersion,
      message: err?.message || '检查更新失败',
    }
  }
}

async function getCurrentReleaseNotes() {
  const version = app.getVersion()
  try {
    for (const tag of [`v${version}`, version]) {
      const response = await net.fetch(`https://api.github.com/repos/Ackow/EchoTalk/releases/tags/${encodeURIComponent(tag)}`, {
        headers: { Accept: 'application/vnd.github+json', 'User-Agent': `EchoTalk/${version}` },
        signal: AbortSignal.timeout(8000),
      })
      if (response.status === 404) continue
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const release = await response.json()
      return { highlights: extractHighlights(release.body), url: `https://github.com/Ackow/EchoTalk/releases/tag/${encodeURIComponent(tag)}` }
    }
    return { highlights: [], url: '' }
  } catch {
    return { highlights: [], url: '' }
  }
}

// 开发模式下用 F12 / Ctrl(Cmd)+Shift+I 切换开发者工具。
// 不用全局快捷键（会抢占系统级组合键），也不用菜单角色——autoHideMenuBar 已隐藏菜单，
// 菜单加速器在无菜单栏时并不可靠，before-input-event 直接作用于本窗口最稳。
function isDevtoolsShortcut(input) {
  if (input.type !== 'keyDown') return false
  if (input.key === 'F12' || input.code === 'F12') return true // F12 各平台一致
  const key = input.key?.toLowerCase()
  if (key !== 'i') return false
  // Ctrl+Shift+I（Win/Linux）、Cmd+Alt+I / Cmd+Shift+I（macOS）
  return (input.control && input.shift) || (input.meta && (input.alt || input.shift))
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1280, // 留出品牌区与完整账户工作区
    height: 830,
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
      nodeIntegration: false, // 关闭 Node 集成，保证渲染进程安全
      // 打包后彻底关闭开发者工具：避免渲染层被随意查看与注入
      devTools: !app.isPackaged
    }
  })

  mainWindow = window
  window.on('closed', () => {
    if (mainWindow === window) mainWindow = null
  })

  if (app.isPackaged) window.loadFile(path.join(__dirname, '../dist/index.html')) // 打包后加载本地构建产物
  else window.loadURL('http://127.0.0.1:5173') // 开发时加载 Vite 开发服务器

  // 仅开发环境注册快捷键；打包后即使拿到按键也不会打开开发者工具
  if (!app.isPackaged) {
    const bindDevtoolsShortcut = (wc) => {
      wc.on('before-input-event', (event, input) => {
        if (!isDevtoolsShortcut(input)) return
        event.preventDefault() // 拦掉默认行为，避免与页面内快捷键重复触发
        if (window.webContents.isDevToolsOpened()) {
          window.webContents.closeDevTools()
        } else {
          window.webContents.openDevTools({ mode: 'detach' })
        }
      })
    }
    bindDevtoolsShortcut(window.webContents)
    // DevTools 自身获得焦点时，主 webContents 收不到按键，需同步绑定以便再次按 F12 收起
    window.webContents.on('devtools-opened', () => {
      if (window.webContents.devToolsWebContents) {
        bindDevtoolsShortcut(window.webContents.devToolsWebContents)
      }
    })
  }

  window.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url) // 外部 https 链接交给系统浏览器
    return { action: 'deny' } // 应用内一律禁止新开窗口
  })
}

app.whenReady().then(() => {
  ipcMain.handle('get-app-version', () => app.getVersion()) // 渲染进程查询应用版本
  ipcMain.handle('get-current-release-notes', () => getCurrentReleaseNotes())
  ipcMain.handle('check-for-updates', () => checkForUpdates())
  ipcMain.handle('open-external', (_event, url) => {
    if (typeof url === 'string' && /^https?:\/\//i.test(url)) {
      return shell.openExternal(url)
    }
    return false
  })
  createWindow() // 窗口控制按钮由 titleBarOverlay 原生提供，无需应用内 IPC 转发

  // 打包环境下启动 5 秒后静默检测一次新版本，有更新再通知渲染进程
  if (app.isPackaged) {
    setTimeout(async () => {
      const result = await checkForUpdates()
      if (result.status === 'available' && mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('update-available', result)
      }
    }, 5000)
  }

  app.on('activate', () => { // macOS 点 Dock 图标时若无窗口则重建
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit() // 非 macOS 关闭全部窗口即退出应用
})
