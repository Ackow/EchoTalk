// 应用入口：挂载 Vue 根组件和路由。
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/styles.css' // 全局样式

// 标记运行平台，CSS 据此处理 macOS 红绿灯留白等差异；浏览器环境无此标记。
document.documentElement.dataset.platform = window.electronAPI?.platform || ''

createApp(App).use(router).mount('#app') // 只装路由，无其他全局插件
