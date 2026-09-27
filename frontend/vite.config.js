// Vite 构建配置。
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const configuredApi = env.VITE_API_BASE_URL
  if (mode === 'production' && !configuredApi) {
    throw new Error('正式构建前请在 frontend/.env.production.local 配置云端 VITE_API_BASE_URL')
  }
  if (mode === 'production' && new URL(configuredApi).protocol !== 'https:') {
    throw new Error('正式构建的 VITE_API_BASE_URL 必须使用 HTTPS')
  }
  const apiBaseUrl = configuredApi || 'http://127.0.0.1:8000'
  const apiOrigin = new URL(apiBaseUrl).origin

  return {
    plugins: [
      vue(), // Vue 单文件组件支持
      {
        name: 'echotalk-api-csp',
        transformIndexHtml(html) {
          // CSP 只放行当前构建配置的 API 源，开发与打包统一读取 VITE_API_BASE_URL。
          const devOrigins = mode === 'development' ? 'http://127.0.0.1:5173 ws://127.0.0.1:5173' : ''
          const devInline = mode === 'development' ? "'unsafe-inline'" : ''
          const devEval = mode === 'development' ? "'unsafe-eval'" : ''
          return html
            .replace('__ECHOTALK_API_ORIGIN__', apiOrigin)
            .replace('__ECHOTALK_DEV_ORIGINS__', devOrigins)
            .replaceAll('__ECHOTALK_DEV_INLINE__', devInline)
            .replace('__ECHOTALK_DEV_EVAL__', devEval)
        }
      }
    ],
    base: './', // Electron 生产环境构建必须使用相对路径
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src') // @ 指向 src 目录
      }
    },
    server: {
      host: '127.0.0.1', // 显式绑定 IPv4 回环：与 electron 的 wait-on/loadURL(127.0.0.1) 保持一致，避免 Vite 默认只绑 IPv6 ::1 导致连不上
      port: 5173, // 固定开发端口，与 Electron 主进程约定一致
      strictPort: true // 端口被占用时直接报错，不自动换端口
    }
  }
})
