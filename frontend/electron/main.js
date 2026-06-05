const { app, BrowserWindow, ipcMain, session } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

let backendProcess = null

function startBackend() {
  if (!app.isPackaged) {
    // 开发环境：拉起本地 .venv 中的 python 服务
    // 相对路径解析：从 frontend/electron/main.js 定位到根目录的 .venv
    const pythonBin = path.resolve(__dirname, '..', '..', '.venv', 'Scripts', 'python.exe')
    const scriptPath = path.resolve(__dirname, '..', '..', 'backend', 'main.py')
    const backendCwd = path.resolve(__dirname, '..', '..', 'backend')
    
    console.log(`[Electron] 正在开发环境拉起 Python 后端: ${pythonBin} ${scriptPath}`)
    backendProcess = spawn(pythonBin, [scriptPath], {
      cwd: backendCwd,
      stdio: 'pipe'
    })
  } else {
    // 生产环境：拉起打包在 resources 目录下的 echotalk-backend.exe 进程
    const backendBin = path.resolve(process.resourcesPath, 'backend', 'echotalk-backend.exe')
    const backendCwd = path.resolve(process.resourcesPath, 'backend')
    
    console.log(`[Electron] 正在生产环境拉起已打包的后端: ${backendBin}`)
    backendProcess = spawn(backendBin, [], {
      cwd: backendCwd,
      stdio: 'pipe'
    })
  }

  if (backendProcess) {
    backendProcess.stdout.on('data', (data) => {
      console.log(`[Backend STDOUT]: ${data.toString().trim()}`)
    })
    backendProcess.stderr.on('data', (data) => {
      console.error(`[Backend STDERR]: ${data.toString().trim()}`)
    })
    backendProcess.on('close', (code) => {
      console.log(`[Backend] 后端服务进程退出，退出码: ${code}`)
    })
  }
}

function killBackend() {
  if (backendProcess) {
    console.log('[Electron] 正在关闭 Python 后端服务进程...')
    backendProcess.kill('SIGINT') // 发送 SIGINT 优雅退出
    backendProcess = null
  }
}

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 1000,
    minHeight: 700,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: true
    },
    autoHideMenuBar: true // 隐藏默认菜单栏以获得高端的自定义视觉效果
  })

  // 开发环境加载 Vite 热更新服务，生产环境加载打包后的静态 HTML
  if (!app.isPackaged) {
    mainWindow.loadURL('http://127.0.0.1:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })
}

app.whenReady().then(() => {
  // 1. 媒体设备（麦克风）权限自动授权配置
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media') {
      return callback(true) // 自动允许录音权限申请
    }
    callback(false)
  })

  session.defaultSession.setPermissionCheckHandler((webContents, permission, origin) => {
    if (permission === 'media') {
      return true
    }
    return false
  })

  // 2. 自动拉起后端服务进程
  startBackend()

  // 3. 创建应用窗口
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('will-quit', () => {
  // 退出时确保杀死子进程，不留脏进程
  killBackend()
})

// IPC 通信：供前端拉取当前桌面应用版本
ipcMain.handle('get-app-version', () => app.getVersion())

